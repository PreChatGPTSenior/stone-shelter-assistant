import json
from collections.abc import Awaitable
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal, NotRequired, Protocol, cast

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_json_schema
from langchain_openrouter import ChatOpenRouter
from langgraph.config import get_config
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field, ValidationError

from stone_shelter_assistant.assistant.budget import RunBudget
from stone_shelter_assistant.assistant.candidate_assessment import (
    CandidateEvaluation,
    evaluate_candidate,
)
from stone_shelter_assistant.assistant.candidate_criteria import (
    CompatibilityTarget,
    QuotedCriterion,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.candidate_evidence import (
    AssessmentStatus,
    CandidateEvidence,
    SourceText,
    assessment_failure_status,
    assessment_source_text,
    candidate_sources,
)
from stone_shelter_assistant.assistant.candidate_ranking import recommendation_order
from stone_shelter_assistant.assistant.prompts.answer import build_answer_messages
from stone_shelter_assistant.assistant.prompts.candidate_evidence import (
    build_candidate_evidence_messages,
)
from stone_shelter_assistant.assistant.prompts.grounding import build_grounding_messages
from stone_shelter_assistant.assistant.prompts.parsing import build_parsing_messages
from stone_shelter_assistant.assistant.prompts.reference_answer import (
    build_reference_answer_messages,
)
from stone_shelter_assistant.assistant.prompts.reference_evidence import (
    build_reference_evidence_messages,
)
from stone_shelter_assistant.assistant.prompts.selection import build_selection_messages
from stone_shelter_assistant.assistant.question_grounding import (
    GroundingProposal,
    GroundingResponse,
    validate_grounding_response,
    validate_question_coverage,
)
from stone_shelter_assistant.assistant.ranking_policy import RANKING_POLICY
from stone_shelter_assistant.assistant.reference_evidence import (
    SCOPE_TITLES,
    GroundedReferenceQuote,
    ReferenceAnswer,
    ReferenceEvidence,
    check_reference_quotes,
    reference_citations_valid,
)
from stone_shelter_assistant.assistant.reference_lookup import (
    ReferenceResult,
    ReferenceTools,
    read_reference,
)
from stone_shelter_assistant.assistant.selection import (
    ParseQuestion,
    RetrievalRequest,
    SelectCandidates,
    question_fragments,
    validate_parsed_atoms,
)
from stone_shelter_assistant.assistant.tool_planning import (
    PlannedTool,
    ReferenceRequest,
    ToolPlan,
    deterministic_tool_plan,
    permitted_tools,
    plan_error,
)
from stone_shelter_assistant.search.document_models import (
    DEFAULT_LANGUAGE,
    CompatibilityPairSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.knowledge.grounding_concept_store_service import (
    GroundingConceptStoreService,
    GroundingSnapshot,
)
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
)
from stone_shelter_assistant.stones.enums import StoneType
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

MAX_SEARCH_TOOL_CALLS = 4
SEARCH_TOOL_NAMES = {"search_stones_lexical", "search_stones_semantic", "search_stones_hybrid"}
PLACEHOLDER_RESERVE = Decimal("0")


class SearchState(MessagesState):
    question: str
    parsed_question: NotRequired[ParseQuestion]
    grounding_status: NotRequired[str]
    grounding_error_type: NotRequired[str]
    question_coverage_status: NotRequired[str]
    question_coverage_audit: NotRequired[dict[str, object]]
    grounding_catalog: NotRequired[dict[str, object]]
    grounding_catalog_snapshot: NotRequired[dict[str, object]]
    grounding_catalog_error_type: NotRequired[str]
    grounding_decisions: NotRequired[list[dict[str, object]]]
    tools_used: int
    search_end_reason: NotRequired[str]
    question_fragments: NotRequired[dict[int, str]]
    selection_status: NotRequired[str]
    selection_note: NotRequired[str]
    selection_output_method: NotRequired[str]
    duplicate_criteria_removed: NotRequired[int]
    selected_stone_ids: NotRequired[list[str]]
    candidate_cards: NotRequired[dict[str, dict[str, object]]]
    verified_statuses: NotRequired[dict[str, str]]
    retrieval: NotRequired[RetrievalRequest]
    parser_diagnostics: NotRequired[list[dict[str, object]]]
    selection_decisions: NotRequired[list[dict[str, object]]]
    retrieval_provenance: NotRequired[list[dict[str, object]]]
    criteria: NotRequired[SearchCriteria]
    criteria_status: NotRequired[str]
    reference_request: NotRequired[ReferenceRequest]
    permitted_tools: NotRequired[list[PlannedTool]]
    tool_plan: NotRequired[ToolPlan]
    plan_status: NotRequired[str]
    plan_error: NotRequired[str]
    reference_result: NotRequired[ReferenceResult]
    reference_quotes: NotRequired[list[GroundedReferenceQuote]]
    reference_assessment_status: NotRequired[str]
    reference_quote_diagnostics: NotRequired[list[dict[str, str]]]
    reference_answer_status: NotRequired[str]
    reference_component: NotRequired[dict[str, object]]
    assessment_status: NotRequired[AssessmentStatus]
    assessment_output_method: NotRequired[str | None]
    candidate_evaluations: NotRequired[list[dict[str, object]]]
    evaluation_sources: NotRequired[dict[str, dict[str, object]]]
    recommended_stone_ids: NotRequired[list[str]]
    evaluation_policy: NotRequired[str]
    ranking_policy: NotRequired[dict[str, object]]
    model_call: NotRequired[dict[str, object]]
    stop_reason: NotRequired[str]
    result: NotRequired[dict[str, object]]


@dataclass(frozen=True)
class WorkflowModels:
    selection_model: ChatOpenRouter
    selection_uses_json_schema: bool
    parsing_model: ChatOpenRouter
    evaluation_model: ChatOpenRouter
    evaluation_uses_json_schema: bool
    answer_model: ChatOpenRouter
    evaluation_reasoning: dict[str, object] | None = None


@dataclass(frozen=True)
class WorkflowTools:
    retrieval: tuple[BaseTool, ...]
    details_tool: BaseTool
    status_tool: BaseTool
    timeline_tool: BaseTool
    compatibility_tool: BaseTool
    encyclopedia_tool: BaseTool
    reference_tools: ReferenceTools


@dataclass(frozen=True)
class RunContext:
    grounding_catalog: GroundingConceptStoreService
    models: WorkflowModels
    tools: WorkflowTools
    tool_executor: ToolNode
    budget: RunBudget


class CandidateExplanation(BaseModel):
    stone_id: str
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)


class AnswerDraft(BaseModel):
    explanations: list[CandidateExplanation] = Field(default_factory=list)


@dataclass(frozen=True)
class CandidateEvaluationInputs:
    criteria: SearchCriteria | None
    cards: list[StoneDetails]
    statuses: dict[str, str]
    pairs: dict[str, CompatibilityPairSearchDocument | None]
    character: list[QuotedCriterion]
    targets: dict[StoneType, CompatibilityTarget]
    encyclopedia: dict[StoneType, EncyclopediaSectionSearchDocument]
    texts: dict[str, dict[str, SourceText]]


@dataclass(frozen=True)
class CandidateAssessmentResult:
    evidence: CandidateEvidence
    status: AssessmentStatus
    output_method: str | None
    model_details: dict[str, object]


@dataclass(frozen=True)
class CandidateAnswerInputs:
    cards: dict[str, dict[str, object]]
    card_sources: dict[str, dict[str, object]]
    evaluation_sources: dict[str, dict[str, object]]
    evidence: dict[str, dict[str, object]]
    statuses: dict[str, str]
    recommendations: list[str]
    evaluations: dict[str, CandidateEvaluation]
    ordered_ids: dict[str, None]
    explainable: dict[str, CandidateEvaluation]
    allowed_evidence_ids: dict[str, list[str]]


@dataclass(frozen=True)
class GroundingAuditResult:
    supported: frozenset[str]
    updates: dict[str, object]
    failure: dict[str, str] | None = None


def candidate_explanation_evidence_ids(
    stone_id: str,
    evaluation: CandidateEvaluation,
    available_sources: dict[str, dict[str, object]],
) -> list[str]:
    """Return card and validated reason sources allowed for one candidate's prose."""
    allowed = {f"stone-card:{stone_id}"} & available_sources.keys()
    for reason in evaluation.reasons:
        if reason.criterion == "availability":
            continue
        allowed.update(
            item.source_id for item in reason.evidence if item.source_id in available_sources
        )
    return sorted(allowed)


class WorkflowNode(Protocol):
    def __call__(
        self, state: SearchState, *, runtime: Runtime[RunContext]
    ) -> Awaitable[dict[str, object]]: ...


# Defines the workflow topology and returns the compiled LangGraph.
# Registers retrieval and evaluation nodes and budget-wraps model stages,
# and connects each node to its fixed or conditional transition.
def build_graph() -> CompiledStateGraph[SearchState, RunContext, SearchState, SearchState]:
    builder = StateGraph(SearchState, context_schema=RunContext)
    # node
    builder.add_node("search_candidates", search_candidates)
    builder.add_node("tools", tools)
    builder.add_node("select_candidates", with_model_budget(select_candidates))
    builder.add_node("parse_question", with_model_budget(parse_question))
    builder.add_node("ground_question", with_model_budget(ground_question))
    builder.add_node("plan_tools", plan_tools)
    builder.add_node("execute_reference_plan", execute_reference_plan)
    builder.add_node("collect_reference_evidence", with_model_budget(collect_reference_evidence))
    builder.add_node("answer_reference", answer_reference)
    builder.add_node("continue_mixed", continue_mixed)
    builder.add_node("clarify_request", clarify_request)
    builder.add_node("read_candidate_cards", read_candidate_cards)
    builder.add_node("verify", verify)
    builder.add_node("evaluate_candidates", with_model_budget(evaluate_candidates))
    builder.add_node("answer", with_model_budget(answer))
    builder.add_node("stop", stop)
    # edge
    builder.add_edge(START, "parse_question")
    builder.add_conditional_edges("parse_question", after_parsing)
    builder.add_edge("ground_question", "plan_tools")
    builder.add_conditional_edges("plan_tools", after_planning)
    builder.add_edge("execute_reference_plan", "collect_reference_evidence")
    builder.add_conditional_edges("collect_reference_evidence", after_reference_evidence)
    builder.add_conditional_edges(
        "answer_reference",
        after_reference_answer,
        {"done": END, "mixed": "continue_mixed"},
    )
    builder.add_edge("continue_mixed", "search_candidates")
    builder.add_edge("clarify_request", END)
    builder.add_conditional_edges("search_candidates", after_retrieval_request)
    builder.add_edge("tools", "select_candidates")
    builder.add_conditional_edges("select_candidates", after_selection)
    builder.add_edge("read_candidate_cards", "verify")
    builder.add_edge("verify", "evaluate_candidates")
    builder.add_conditional_edges("evaluate_candidates", after_evaluation)
    builder.add_conditional_edges("answer", after_answer, {"stop": "stop", "done": END})
    builder.add_edge("stop", END)

    return builder.compile()


# Starts one question run and returns the result set by answer or stop.
# Calls build_graph, creates the initial state, and awaits graph.ainvoke
# with the supplied search and status tools and a fresh budget in RunContext.
async def run_workflow(
    question: str,
    models: WorkflowModels,
    tools: WorkflowTools,
    grounding_catalog: GroundingConceptStoreService,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    graph = build_graph()
    state = await graph.ainvoke(
        {
            "question": question,
            "messages": [HumanMessage(content=question)],
            "tools_used": 0,
        },
        config=config,
        context=RunContext(
            grounding_catalog=grounding_catalog,
            models=models,
            tools=tools,
            tool_executor=ToolNode(tools.retrieval),
            budget=RunBudget(),
        ),
    )
    return cast(dict[str, object], state["result"])


# Collects each card returned by a successful stone search once.
def retrieved_candidates(state: SearchState) -> dict[str, dict[str, object]]:
    candidates: dict[str, dict[str, object]] = {}
    for message in state["messages"]:
        if (
            isinstance(message, ToolMessage)
            and message.name in SEARCH_TOOL_NAMES
            and message.status == "success"
        ):
            try:
                hits = (
                    json.loads(message.content)
                    if isinstance(message.content, str)
                    else message.content
                )
            except ValueError:
                continue
            if message.name == "search_stones_hybrid" and isinstance(hits, dict):
                hits = [item["card"] for item in hits["candidates"]]
            if isinstance(hits, list):
                for hit in hits:
                    if isinstance(hit, dict) and isinstance(stone_id := hit.get("id"), str):
                        candidates.setdefault(stone_id, hit)
    return candidates


# Captures the model and billing metadata that OpenRouter actually reported.
def model_call_details(reply: AIMessage) -> dict[str, object]:
    details: dict[str, object] = {
        key: reply.response_metadata[key]
        for key in ("model_name", "provider", "id", "cost", "finish_reason")
        if reply.response_metadata.get(key) is not None
    }
    if reply.usage_metadata is not None:
        details["usage"] = dict(reply.usage_metadata)
    return details


def grounding_catalog_summary(snapshot: GroundingSnapshot) -> dict[str, object]:
    return {
        "language": snapshot.language,
        "version": snapshot.catalog_version,
        "content_hash": snapshot.content_hash,
        "entry_ids": [entry.id for entry in snapshot.entries],
    }


# Nodes


# Build exactly one prepared retrieval call without another model invocation.
async def search_candidates(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    request = state["reference_request"]
    if request.recommendation_name:
        name = "search_stones_lexical"
        args: dict[str, object] = {"query": request.recommendation_name}
    else:
        name = "search_stones_hybrid"
        args = state["retrieval"].model_dump(mode="json")
    cost = retrieval_call_cost(runtime.context.tool_executor.tools_by_name[name])
    if state["tools_used"] + cost > MAX_SEARCH_TOOL_CALLS:
        return {"stop_reason": "retrieval_call_limit", "search_end_reason": "tool_limit"}
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": name, "args": args, "id": "candidate-search", "type": "tool_call"}
                ],
            )
        ],
        "search_end_reason": "prepared_retrieval",
    }


def retrieval_call_cost(tool: BaseTool) -> int:
    return int((tool.metadata or {}).get("retrieval_calls", 1))


def after_retrieval_request(state: SearchState) -> Literal["stop", "tools"]:
    return "stop" if state.get("stop_reason") else "tools"


# Executes the bounded tool batch and counts each retrieval call separately.
async def tools(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    message = state["messages"][-1]
    assert isinstance(message, AIMessage)
    update = await runtime.context.tool_executor.ainvoke(
        state, config=get_config(), runtime=runtime
    )
    used = state["tools_used"] + sum(
        retrieval_call_cost(runtime.context.tool_executor.tools_by_name[call["name"]])
        for call in message.tool_calls
    )
    result: dict[str, object] = {**update, "tools_used": used}
    provenance = []
    for response in update.get("messages", []):
        if isinstance(response, ToolMessage) and response.name == "search_stones_hybrid":
            if response.status == "error":
                raise RuntimeError("Hybrid retrieval failed")
            payload = (
                json.loads(response.content)
                if isinstance(response.content, str)
                else response.content
            )
            if isinstance(payload, dict):
                for hit in [*payload["candidates"], *payload["dropped"]]:
                    card = hit["card"]
                    provenance.append(
                        {
                            **{key: value for key, value in hit.items() if key != "card"},
                            "stone_id": card["id"],
                            "external_id": card["stone_external_id"],
                            "name": card["title"],
                            "explanation": f"Typesense #{hit['lexical_rank']}; Qdrant #{hit['semantic_rank']}; "
                            f"RRF {hit['rrf_score']:.6f}; rank #{hit['retrieval_rank']}",
                        }
                    )
    result["retrieval_provenance"] = provenance
    if used >= MAX_SEARCH_TOOL_CALLS:
        result["search_end_reason"] = "tool_limit"
    return result


# Uses strict schema only for models whose provider advertises support.
def structured_model(
    model: ChatOpenRouter,
    schema: type[BaseModel],
    *,
    use_json_schema: bool,
    reasoning: dict[str, object] | None = None,
) -> tuple[str, Runnable[LanguageModelInput, dict[str, Any] | BaseModel]]:
    reasoning = {"enabled": False} if reasoning is None else reasoning
    if use_json_schema:
        # langchain-openrouter 0.2.9 sets strict on the outer response format,
        # but does not pass it to convert_to_json_schema. Normalize the wire
        # schema here, then validate the decoded object with the original DTO.
        wire_schema = convert_to_json_schema(schema, strict=True)
        structured = model.with_structured_output(
            wire_schema,
            method="json_schema",
            strict=True,
            include_raw=True,
            provider={"require_parameters": True},
            reasoning=reasoning,
        )
        def validate_typed_response(response: Any) -> Any:
            if (
                not isinstance(response, dict)
                or "parsed" not in response
                or response.get("parsing_error") is not None
            ):
                return response
            try:
                parsed = schema.model_validate(response["parsed"])
            except ValidationError as error:
                return {**response, "parsed": None, "parsing_error": error}
            return {**response, "parsed": parsed}

        return "json_schema", cast(
            Runnable[LanguageModelInput, dict[str, Any] | BaseModel],
            structured.pipe(RunnableLambda(validate_typed_response)),
        )
    return "function_calling", model.with_structured_output(
        schema, method="function_calling", include_raw=True, reasoning=reasoning
    )


# Keeps only retrieved IDs and caps the shortlist after removing duplicates.
async def select_candidates(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    candidates = retrieved_candidates(state)
    request = state.get("reference_request")
    if request is not None and request.recommendation_name is not None:
        reference = state.get("reference_result")
        issue = reference.recommendation_issue if reference is not None else "not_resolved"
        identity = reference.recommendation_stone if reference is not None else None
        if issue is not None or identity is None:
            note = (
                f"The name {request.recommendation_name} matches multiple stones; please clarify."
                if issue == "ambiguous"
                else f"No stone was found with the name {request.recommendation_name}."
                if issue == "not_found"
                else f"The name {request.recommendation_name} could not be resolved; no recommendation was selected."
            )
            return {
                "selected_stone_ids": [],
                "selection_status": "named_target_" + (issue or "not_resolved"),
                "selection_note": note,
            }
        exact_id = str(identity.stone_id)
        if exact_id not in candidates:
            return {
                "selected_stone_ids": [],
                "selection_status": "named_candidate_not_retrieved",
                "selection_note": (
                    f"{request.recommendation_name} was found in PostgreSQL but not in the "
                    "candidate search results, so no substitute was selected."
                ),
            }
        candidates = {exact_id: candidates[exact_id]}
    if not candidates:
        return {"selected_stone_ids": [], "selection_status": "no_search_results"}

    criteria = state.get("criteria")
    if criteria is None:
        return {"selected_stone_ids": [], "selection_status": "missing_criteria"}

    context = runtime.context
    method, model = structured_model(
        context.models.selection_model,
        SelectCandidates,
        use_json_schema=context.models.selection_uses_json_schema,
    )
    response = await model.ainvoke(
        build_selection_messages(
            question=state["question"],
            criteria=criteria.model_dump(mode="json"),
            reference_request=(
                state["reference_request"].model_dump(mode="json")
                if "reference_request" in state
                else None
            ),
            retrieved_cards=list(candidates.values()),
            retrieval_provenance=state.get("retrieval_provenance", []),
        ),
        config=get_config(),
    )
    result: dict[str, object] = {
        "selected_stone_ids": [],
        "selection_status": "invalid_selection",
        "selection_output_method": method,
        "selection_decisions": [
            {"stone_id": stone_id, "selected": False} for stone_id in candidates
        ],
    }
    if not isinstance(response, dict) or not isinstance(raw := response.get("raw"), AIMessage):
        return result
    result["model_call"] = model_call_details(raw)
    parsed = response.get("parsed")
    if raw.response_metadata.get("finish_reason") == "length" or not isinstance(
        parsed, SelectCandidates
    ):
        return result
    grounded_ids = [
        stone_id for stone_id in dict.fromkeys(parsed.stone_ids) if stone_id in candidates
    ]
    return {
        **result,
        "selection_status": "selected",
        "selected_stone_ids": grounded_ids[: RANKING_POLICY.shortlist_limit],
        "selection_decisions": [
            {
                "stone_id": stone_id,
                "selected": stone_id in grounded_ids[: RANKING_POLICY.shortlist_limit],
            }
            for stone_id in candidates
        ],
    }


# Parses the question once without giving the model any retrieved candidate data.
async def parse_question(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    fragments = question_fragments(state["question"])
    result: dict[str, object] = {
        "question_fragments": fragments,
        "criteria_status": "invalid_criteria",
    }
    catalog_snapshot: GroundingSnapshot | None = None
    try:
        loaded_snapshot = await runtime.context.grounding_catalog.load()
        catalog_snapshot = GroundingSnapshot.model_validate(loaded_snapshot)
    except Exception as error:
        result["grounding_catalog_error_type"] = type(error).__name__
    if catalog_snapshot is not None:
        result["grounding_catalog"] = grounding_catalog_summary(catalog_snapshot)
        result["grounding_catalog_snapshot"] = catalog_snapshot.model_dump(mode="json")
    model = runtime.context.models.parsing_model.with_structured_output(
        ParseQuestion, method="function_calling", include_raw=True, reasoning={"enabled": False}
    )
    response = await model.ainvoke(
        build_parsing_messages(
            question=state["question"],
            question_fragments=[
                {"fragment_id": fragment_id, "text": text}
                for fragment_id, text in fragments.items()
            ],
            semantic_concepts=(
                {
                    "language": catalog_snapshot.language,
                    "version": catalog_snapshot.catalog_version,
                    "content_hash": catalog_snapshot.content_hash,
                    "entries": [
                        entry.model_dump(mode="json", exclude_none=True)
                        for entry in catalog_snapshot.entries
                    ],
                }
                if catalog_snapshot is not None
                else None
            ),
            default_recommendation_limit=RANKING_POLICY.default_recommendation_limit,
        ),
        config=get_config(),
    )
    if not isinstance(response, dict) or not isinstance(raw := response.get("raw"), AIMessage):
        return result
    result["model_call"] = model_call_details(raw)
    parsed = response.get("parsed")
    if raw.response_metadata.get("finish_reason") == "length" or not isinstance(
        parsed, ParseQuestion
    ):
        return result
    return {**result, "parsed_question": parsed, "criteria_status": "pending_grounding"}


async def ground_question(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    """Verify sensitive proposals and audit parsed atom coverage in one semantic call."""
    parsed = state.get("parsed_question")
    if parsed is None:
        return {"grounding_status": "not_reached"}
    fragments = state["question_fragments"]
    try:
        proposals = parsed.grounding_proposals(fragments)
        atoms = parsed.parsed_atoms(fragments)
        validate_parsed_atoms(atoms, fragments)
    except (KeyError, ValueError):
        return {
            "criteria_status": "invalid_criteria_fragments",
            "grounding_status": "invalid_proposals",
            "question_coverage_status": "invalid_atoms",
        }
    supported: frozenset[str] = frozenset()
    audit_required = bool(proposals) or parsed.recommendation_limit > 0
    if audit_required:
        audit = await _run_grounding_audit(state, runtime, parsed, fragments, proposals, atoms)
        result = {
            "grounding_status": "not_needed",
            "question_coverage_status": "not_run",
            **audit.updates,
        }
        if audit.failure:
            return {**result, **audit.failure}
        supported = audit.supported
    else:
        result = {
            "grounding_status": "not_needed",
            "question_coverage_status": "not_run",
        }
    return _resolve_grounded_question(parsed, fragments, proposals, supported, result)


async def _run_grounding_audit(
    state: SearchState,
    runtime: Runtime[RunContext],
    parsed: ParseQuestion,
    fragments: dict[int, str],
    proposals: list[GroundingProposal],
    atoms: list[dict[str, object]],
) -> GroundingAuditResult:
    catalog, failure = _resolve_grounding_catalog(state)
    if failure is not None:
        return GroundingAuditResult(frozenset(), {}, failure)
    assert catalog is not None
    updates: dict[str, object] = {"grounding_catalog": grounding_catalog_summary(catalog)}
    _, model = structured_model(
        runtime.context.models.evaluation_model,
        GroundingResponse,
        use_json_schema=runtime.context.models.evaluation_uses_json_schema,
        reasoning=runtime.context.models.evaluation_reasoning,
    )
    try:
        response = await model.ainvoke(
            build_grounding_messages(
                catalog,
                state["question"],
                fragments,
                proposals,
                atoms,
                parsed.model_dump(mode="json"),
                ParseQuestion.model_json_schema(),
            ),
            config=get_config(),
        )
    except Exception as error:
        return GroundingAuditResult(
            frozenset(),
            updates,
            {"grounding_status": "grounding_model_error", "grounding_error_type": type(error).__name__},
        )
    return _validate_grounding_model_response(response, proposals, atoms, fragments, updates)


def _resolve_grounding_catalog(
    state: SearchState,
) -> tuple[GroundingSnapshot | None, dict[str, str] | None]:
    catalog_error = state.get("grounding_catalog_error_type")
    if catalog_error is not None:
        return None, {
            "grounding_status": "grounding_unavailable",
            "grounding_error_type": catalog_error,
        }
    catalog_snapshot = state.get("grounding_catalog_snapshot")
    if catalog_snapshot is None:
        return None, {
            "grounding_status": "grounding_unavailable",
            "grounding_error_type": "GroundingSnapshotMissing",
        }
    try:
        return GroundingSnapshot.model_validate(catalog_snapshot), None
    except ValidationError:
        return None, {
            "grounding_status": "grounding_unavailable",
            "grounding_error_type": "GroundingSnapshotInvalid",
        }


def _validate_grounding_model_response(
    response: object,
    proposals: list[GroundingProposal],
    atoms: list[dict[str, object]],
    fragments: dict[int, str],
    updates: dict[str, object],
) -> GroundingAuditResult:
    if not isinstance(response, dict) or not isinstance(raw := response.get("raw"), AIMessage):
        return GroundingAuditResult(
            frozenset(), updates, {"grounding_status": "invalid_grounding_response"}
        )
    updates["model_call"] = model_call_details(raw)
    verdicts = response.get("parsed")
    if raw.response_metadata.get("finish_reason") == "length" or not isinstance(
        verdicts, GroundingResponse
    ):
        return GroundingAuditResult(
            frozenset(), updates, {"grounding_status": "invalid_grounding_response"}
        )
    try:
        supported = validate_grounding_response(verdicts, proposals, fragments)
        validate_question_coverage(verdicts.question_coverage, atoms, fragments)
    except (ValueError, KeyError):
        return GroundingAuditResult(
            frozenset(),
            updates,
            {
                "grounding_status": "invalid_grounding_binding",
                "question_coverage_status": "invalid_audit",
            },
        )
    if proposals:
        updates["grounding_status"] = "verified"
        updates["grounding_decisions"] = [
            decision.model_dump(mode="json") for decision in verdicts.decisions
        ]
    updates["question_coverage_status"] = verdicts.question_coverage.status
    updates["question_coverage_audit"] = verdicts.question_coverage.model_dump(mode="json")
    return GroundingAuditResult(supported, updates)


def _resolve_grounded_question(
    parsed: ParseQuestion,
    fragments: dict[int, str],
    proposals: list[GroundingProposal],
    supported: frozenset[str],
    result: dict[str, object],
) -> dict[str, object]:
    if proposals and "candidate_type" in {proposal.proposal_id for proposal in proposals} and (
        "candidate_type" not in supported
    ):
        return {**result, "criteria_status": "unverified_candidate_type"}
    try:
        criteria, duplicates = parsed.resolve(fragments, supported)
        retrieval = parsed.resolve_retrieval(fragments, supported)
        diagnostics = parsed.grounding_diagnostics(fragments, supported)
        request = parsed.resolve_references(fragments)
    except (KeyError, ValueError):
        return {**result, "criteria_status": "invalid_criteria_fragments"}
    if criteria.recommendation_limit and not request.recommendation_name and retrieval is None:
        return {**result, "criteria_status": "missing_retrieval_request"}
    return {
        **result,
        **({"retrieval": retrieval} if retrieval is not None else {}),
        "criteria": criteria,
        "reference_request": request,
        "criteria_status": "parsed",
        "parser_diagnostics": diagnostics,
        "duplicate_criteria_removed": duplicates,
    }

async def plan_tools(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    """Order the parsed reference and candidate tasks using the code-owned dependencies."""
    del runtime
    criteria = state.get("criteria")
    request = state.get("reference_request")
    if criteria is None or request is None:
        return {"plan_status": "unresolved_question"}
    allowed = permitted_tools(criteria, request)
    blocked_tools: list[str] = []
    if (
        criteria.recommendation_limit
        and state.get("question_coverage_status") != "complete"
        and "search_candidates" in allowed
    ):
        allowed = [tool for tool in allowed if tool != "search_candidates"]
        blocked_tools.append("search_candidates")
    result: dict[str, object] = {
        "permitted_tools": allowed,
        "plan_status": "unresolved_question",
        "blocked_tools": blocked_tools,
    }
    if not allowed:
        if blocked_tools:
            status = state.get("question_coverage_status")
            return {
                **result,
                "plan_status": "question_coverage_incomplete"
                if status in {"incomplete", "uncertain"}
                else "question_coverage_unverified",
            }
        return result
    plan = deterministic_tool_plan(allowed)
    result["tool_plan"] = plan
    if error := plan_error(plan, allowed, request):
        return {**result, "plan_status": "invalid_plan", "plan_error": error}
    return {**result, "plan_status": "accepted"}


async def execute_reference_plan(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    result = await read_reference(
        state["tool_plan"],
        state["reference_request"],
        runtime.context.tools.reference_tools,
        get_config(),
        include_status=bool(state["criteria"].requested_availability),
    )
    return {"reference_result": result}


async def collect_reference_evidence(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    """Use the evidence model once, then validate every returned quotation."""
    sources = state["reference_result"].context_sources
    result: dict[str, object] = {
        "reference_quotes": [],
        "reference_assessment_status": "not_needed",
    }
    if not sources:
        return result
    _, model = structured_model(
        runtime.context.models.evaluation_model,
        ReferenceEvidence,
        use_json_schema=runtime.context.models.evaluation_uses_json_schema,
        reasoning=runtime.context.models.evaluation_reasoning,
    )
    response = await model.ainvoke(
        build_reference_evidence_messages(
            question=state["question"],
            sources=[source.model_dump() for source in sources.values()],
        ),
        config=get_config(),
    )
    result["reference_assessment_status"] = "invalid_response"
    if isinstance(response, dict) and isinstance(raw := response.get("raw"), AIMessage):
        result["model_call"] = model_call_details(raw)
        parsed = response.get("parsed")
        if raw.response_metadata.get("finish_reason") != "length" and isinstance(
            parsed, ReferenceEvidence
        ):
            quotes, rejected = check_reference_quotes(parsed, sources)
            result.update(
                reference_quotes=quotes,
                reference_quote_diagnostics=rejected,
                reference_assessment_status="parsed",
            )
    return result


async def answer_reference(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    """Compose scoped, cited evidence; keep status and pair verdicts deterministic."""
    reference = state["reference_result"]
    quotes = state.get("reference_quotes", [])
    draft, model_details, answer_status = await _generate_reference_answer(state, runtime, quotes)
    request = state["reference_request"]
    recommendation_blocked = _reference_recommendation_blocked(state)
    lines = _render_reference_answer(reference, request, quotes, draft, recommendation_blocked)
    stone = reference.stone
    return {
        "reference_answer_status": answer_status,
        "result": {
            "answer": "\n\n".join(lines),
            "recommendation_status": "blocked_question_coverage" if recommendation_blocked else None,
            "sources": reference.sources,
            "verified_statuses": {str(stone.stone_id): stone.adoption_status.value}
            if stone
            else {},
            "recommended_stone_ids": [],
            "candidate_decisions": [],
        },
        "model_call": model_details,
    }


async def _generate_reference_answer(
    state: SearchState,
    runtime: Runtime[RunContext],
    quotes: list[GroundedReferenceQuote],
) -> tuple[ReferenceAnswer | None, dict[str, object], str]:
    model_details: dict[str, object] = {}
    answer_status = "facts_only"
    if not quotes or not runtime.context.budget.try_reserve(PLACEHOLDER_RESERVE):
        return None, model_details, answer_status
    model = runtime.context.models.answer_model.with_structured_output(
        ReferenceAnswer,
        method="function_calling",
        include_raw=True,
        reasoning={"enabled": False},
    )
    response = await model.ainvoke(
        build_reference_answer_messages(
            question=state["question"],
            quotes=[quote.model_dump() for quote in quotes],
        ),
        config=get_config(),
    )
    answer_status = "invalid_response"
    if not isinstance(response, dict) or not isinstance(raw := response.get("raw"), AIMessage):
        return None, model_details, answer_status
    model_details = model_call_details(raw)
    proposed = response.get("parsed")
    if raw.response_metadata.get("finish_reason") == "length" or not isinstance(
        proposed, ReferenceAnswer
    ):
        return None, model_details, answer_status
    if not reference_citations_valid(proposed, quotes):
        return None, model_details, "invalid_citations"
    return proposed, model_details, "generated"


def _render_reference_answer(
    reference: ReferenceResult,
    request: ReferenceRequest,
    quotes: list[GroundedReferenceQuote],
    draft: ReferenceAnswer | None,
    recommendation_blocked: bool,
) -> list[str]:
    lines = list(reference.lines)
    rendered_raw_source_ids: set[str] = set()
    if draft:
        lines.extend(
            f"**{SCOPE_TITLES[section.scope]}**\n{section.explanation}\nSources: "
            + ", ".join(section.source_ids)
            for section in draft.sections
        )
    elif quotes:
        lines.extend(
            f"**{SCOPE_TITLES[quote.scope]}** · {quote.source_id}\n{quote.quote}"
            for quote in quotes
        )
    elif reference.context_sources:
        lines.append("No validated evidence summary is available. Original sources follow.")
        for source in reference.context_sources.values():
            lines.append(f"**{SCOPE_TITLES[source.scope]}** · {source.source_id}\n{source.text}")
            rendered_raw_source_ids.add(source.source_id)

    rendered_source_ids = (
        {source_id for section in draft.sections for source_id in section.source_ids}
        if draft
        else {quote.source_id for quote in quotes}
        if quotes
        else set(reference.context_sources)
    )
    if quotes and request.stone_info in {"overview", "history"}:
        _append_uncovered_reference_scopes(
            lines, reference, quotes, rendered_source_ids, rendered_raw_source_ids
        )
    _append_uncovered_care_sources(
        lines, reference, request, rendered_raw_source_ids
    )
    _append_exact_pair_sources(lines, reference)
    if recommendation_blocked:
        lines.append(
            "No recommendation was made because the question parser did not account for every "
            "request. Please restate the criteria so each one can be checked."
        )
    return lines


def _append_uncovered_reference_scopes(
    lines: list[str],
    reference: ReferenceResult,
    quotes: list[GroundedReferenceQuote],
    rendered_source_ids: set[str],
    rendered_raw_source_ids: set[str],
) -> None:
    covered = {quote.scope for quote in quotes}
    for source in reference.context_sources.values():
        if source.scope not in covered and source.source_id not in rendered_source_ids:
            lines.append(
                f"**{SCOPE_TITLES[source.scope]}** · {source.source_id}\n"
                f"No validated summary for this scope. Original source:\n{source.text}"
            )
            rendered_source_ids.add(source.source_id)
            rendered_raw_source_ids.add(source.source_id)


def _append_uncovered_care_sources(
    lines: list[str],
    reference: ReferenceResult,
    request: ReferenceRequest,
    rendered_raw_source_ids: set[str],
) -> None:
    care_types = set(request.care_types)
    if request.stone_info == "care" and reference.card is not None:
        care_types.add(reference.card.stone_type)
    if not care_types:
        return
    for source in reference.context_sources.values():
        if (
            source.scope != "encyclopedia"
            or source.source_id in rendered_raw_source_ids
            or source.source_id not in reference.sources
            or source.text in "\n\n".join(lines)
        ):
            continue
        payload = reference.sources[source.source_id].get("data", {})
        document = (
            EncyclopediaSectionSearchDocument.model_validate(payload)
            if isinstance(payload, dict)
            else None
        )
        if document and any(kind in document.stone_types for kind in care_types):
            lines.append(
                f"**{SCOPE_TITLES[source.scope]}** · {source.source_id}\n"
                f"No validated care summary. Original source:\n{source.text}"
            )
            rendered_raw_source_ids.add(source.source_id)


def _append_exact_pair_sources(lines: list[str], reference: ReferenceResult) -> None:
    for source_id in sorted(reference.exact_pair_source_ids):
        source = reference.context_sources[source_id]
        if source.text not in "\n\n".join(lines):
            lines.append(
                f"**{SCOPE_TITLES[source.scope]}** · {source.source_id}\n"
                f"Original pair rule:\n{source.text}"
            )


def _reference_recommendation_blocked(state: SearchState) -> bool:
    criteria = state.get("criteria")
    return bool(
        criteria
        and criteria.recommendation_limit
        and state.get("question_coverage_status") in {"incomplete", "uncertain"}
    )


async def continue_mixed(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    """Retain the completed reference branch before candidate search overwrites result."""
    return {"reference_component": state.get("result", {})}


def combine_mixed_result(
    candidate: dict[str, object], reference: dict[str, object], reference_status: str
) -> dict[str, object]:
    """Combine branch answers without rebinding colliding source citations."""
    sources = candidate.get("sources", {})
    sources = dict(sources) if isinstance(sources, dict) else {}
    reference_sources = reference.get("sources", {})
    reference_answer = reference.get("answer", "")
    answer_text = reference_answer if isinstance(reference_answer, str) else ""
    if isinstance(reference_sources, dict):
        for source_id, source in reference_sources.items():
            if source_id not in sources:
                sources[source_id] = source
            elif sources[source_id] != source:
                alias = f"reference:{source_id}"
                sources[alias] = source
                answer_text = answer_text.replace(str(source_id), alias)
    candidate["sources"] = sources
    existing_answer = candidate.get("answer", "")
    candidate["answer"] = (
        f"{answer_text}\n\n{existing_answer}"
        if answer_text and isinstance(existing_answer, str) and existing_answer
        else answer_text or existing_answer
    )
    ref_statuses = reference.get("verified_statuses", {})
    if isinstance(ref_statuses, dict):
        candidate["reference_verified_statuses"] = ref_statuses
        candidate_statuses = candidate.get("verified_statuses", {})
        if not isinstance(candidate_statuses, dict):
            candidate_statuses = {}
        candidate["verified_statuses"] = {**ref_statuses, **candidate_statuses}
    candidate["reference_answer_status"] = reference_status
    return candidate


def after_reference_answer(state: SearchState) -> Literal["done", "mixed"]:
    criteria = state.get("criteria")
    if (
        criteria is not None
        and criteria.recommendation_limit
        and state.get("question_coverage_status") != "complete"
    ):
        return "done"
    return "mixed" if criteria is not None and criteria.recommendation_limit else "done"


def after_reference_evidence(state: SearchState) -> Literal["stop", "answer_reference"]:
    return "stop" if state.get("stop_reason") else "answer_reference"


def clarify_request(state: SearchState) -> dict[str, object]:
    plan_status = state.get("plan_status")
    grounding_status = state.get("grounding_status")
    message = (
        "I could not build a valid tool plan for this question."
        if plan_status == "invalid_plan"
        else "Please clarify which stone or stone type you mean and what you would like to know."
    )
    if plan_status == "question_coverage_incomplete":
        message = (
            "I did not make a recommendation because the question may contain criteria that were "
            "not captured. Please restate each requirement and preference separately."
        )
    elif plan_status == "question_coverage_unverified":
        message = (
            "I did not make a recommendation because I could not verify that all parts of the "
            "question were captured. Please try again."
        )
    elif grounding_status in {
        "grounding_unavailable",
        "grounding_model_error",
        "invalid_grounding_response",
        "invalid_grounding_binding",
    }:
        message = "The question could not be verified because grounding is unavailable or invalid. Please try again."
    elif state.get("criteria_status") == "unverified_candidate_type":
        message = "Please clarify the required type of the new stone; it could not be verified from the question."
    return {
        "result": {
            "answer": message,
            "plan_status": plan_status,
            "grounding_status": grounding_status,
            "question_coverage_status": state.get("question_coverage_status"),
            "question_coverage_audit": state.get("question_coverage_audit"),
            "sources": {},
            "verified_statuses": {},
            "recommended_stone_ids": [],
            "candidate_decisions": [],
        }
    }


# Reads the shortlisted PostgreSQL cards before the separate status check.
async def read_candidate_cards(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    cards: dict[str, dict[str, object]] = {}
    for stone_id in state.get("selected_stone_ids", []):
        card = await runtime.context.tools.details_tool.ainvoke(
            {"stone_id": stone_id}, config=get_config()
        )
        if card is not None:
            cards[stone_id] = card
    return {"candidate_cards": cards}


# Refreshes the loaded candidates' statuses in one PostgreSQL tool call before answer.
async def verify(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    stone_ids = list(state.get("candidate_cards", {}))
    if not stone_ids:
        return {"verified_statuses": {}}

    rows: list[dict[str, str]] = await runtime.context.tools.status_tool.ainvoke(
        {"stone_ids": stone_ids}, config=get_config()
    )
    return {
        "verified_statuses": {row["stone_id"]: row["adoption_status"] for row in rows},
    }


# Loads missing exact pairs once and reuses matching results from the agent's tool calls.
async def load_compatibility_pairs(
    state: SearchState,
    cards: list[StoneDetails],
    criteria: SearchCriteria,
    tool: BaseTool,
) -> dict[str, CompatibilityPairSearchDocument | None]:
    pairs: dict[str, CompatibilityPairSearchDocument | None] = {}
    for message in state["messages"]:
        if (
            isinstance(message, ToolMessage)
            and message.name == tool.name
            and message.status == "success"
        ):
            try:
                content = (
                    json.loads(message.content)
                    if isinstance(message.content, str)
                    else message.content
                )
                pair = CompatibilityPairSearchDocument.model_validate(content)
            except ValueError:
                continue
            if pair.language == DEFAULT_LANGUAGE and pair.pair_key == build_pair_key(
                *pair.stone_types
            ):
                pairs[pair.pair_key] = pair
    selected_pairs: dict[str, CompatibilityPairSearchDocument | None] = {}
    targets = criteria.compatibility_targets()
    for card in cards:
        for stone_type in targets:
            key = build_pair_key(card.stone_type, stone_type)
            if key not in pairs:
                result = await tool.ainvoke(
                    {"first_type": card.stone_type, "second_type": stone_type},
                    config=get_config(),
                )
                pairs[key] = (
                    CompatibilityPairSearchDocument.model_validate(result) if result else None
                )
            selected_pairs[key] = pairs[key]
    return selected_pairs


# Reads the encyclopedia chapter for each distinct candidate type as general context.
async def load_encyclopedia(
    cards: list[StoneDetails], tool: BaseTool
) -> dict[StoneType, EncyclopediaSectionSearchDocument]:
    chapters = {}
    for stone_type in dict.fromkeys(card.stone_type for card in cards):
        documents = await tool.ainvoke(
            {
                "filters": {
                    "document_kind": DocumentKind.ENCYCLOPEDIA_SECTION,
                    "stone_type": stone_type,
                    "language": DEFAULT_LANGUAGE,
                },
                "limit": 1,
            },
            config=get_config(),
        )
        if documents:
            chapters[stone_type] = EncyclopediaSectionSearchDocument.model_validate(documents[0])
    return chapters


# Interprets quoted evidence, applies the rules and returns a per-candidate trace record.
async def evaluate_candidates(
    state: SearchState, *, runtime: Runtime[RunContext]
) -> dict[str, object]:
    inputs = await _load_candidate_evaluation_inputs(state, runtime)
    assessment = await _assess_candidates(inputs, runtime)
    evaluations = [
        evaluate_candidate(
            inputs.criteria,
            card,
            inputs.statuses.get(str(card.id)),
            inputs.pairs,
            inputs.texts[str(card.id)],
            assessment.evidence,
            assessment.status,
        )
        for card in inputs.cards
    ]
    recommendations = recommendation_order(evaluations, inputs.criteria)
    return {
        "evaluation_policy": RANKING_POLICY.version,
        "ranking_policy": asdict(RANKING_POLICY),
        "criteria_status": state.get("criteria_status", "missing_selection"),
        "assessment_status": assessment.status,
        "assessment_output_method": assessment.output_method,
        "candidate_evaluations": [candidate.model_dump(mode="json") for candidate in evaluations],
        "evaluation_sources": _candidate_evaluation_sources(inputs, runtime),
        "recommended_stone_ids": recommendations,
        "model_call": assessment.model_details,
    }


async def _load_candidate_evaluation_inputs(
    state: SearchState, runtime: Runtime[RunContext]
) -> CandidateEvaluationInputs:
    criteria = state.get("criteria")
    cards = [
        StoneDetails.model_validate(card) for card in state.get("candidate_cards", {}).values()
    ]
    pairs = (
        await load_compatibility_pairs(
            state, cards, criteria, runtime.context.tools.compatibility_tool
        )
        if criteria
        else {}
    )
    character = (
        [*criteria.requirements.character, *criteria.preferences.character] if criteria else []
    )
    targets = criteria.compatibility_targets() if criteria else {}
    encyclopedia = (
        await load_encyclopedia(cards, runtime.context.tools.encyclopedia_tool) if character else {}
    )
    observations = await _load_candidate_observations(cards, runtime) if character or targets else {}
    texts = {
        str(card.id): candidate_sources(
            card, encyclopedia.get(card.stone_type), observations.get(str(card.id), [])
        )
        for card in cards
    }
    return CandidateEvaluationInputs(
        criteria=criteria,
        cards=cards,
        statuses=state.get("verified_statuses", {}),
        pairs=pairs,
        character=character,
        targets=targets,
        encyclopedia=encyclopedia,
        texts=texts,
    )


async def _load_candidate_observations(
    cards: list[StoneDetails], runtime: Runtime[RunContext]
) -> dict[str, list[dict[str, str]]]:
    observations: dict[str, list[dict[str, str]]] = {}
    for card in cards:
        events = await runtime.context.tools.timeline_tool.ainvoke(
            {"case_external_id": str(card.shelter_case.external_id)}, config=get_config()
        )
        unique_events = {
            event["event_external_id"]: event
            for event in events
            if isinstance(event, dict)
            and event.get("event_type") == "OBSERVATION"
            and isinstance(event.get("event_external_id"), str)
        }
        observations[str(card.id)] = list(unique_events.values())
    return observations


def _candidate_evidence_messages(inputs: CandidateEvaluationInputs) -> list[BaseMessage]:
    return build_candidate_evidence_messages(
        character_criteria=[criterion.model_dump() for criterion in inputs.character],
        candidate_sources=[
            {
                "stone_id": stone_id,
                "source_ref": "observation" if source.kind == "observation" else ref,
                "text": assessment_source_text(source),
                **(
                    {
                        "observation_external_id": source.event_external_id,
                        "event_type": source.event_type,
                        "occurred_at": source.occurred_at,
                        "stone_id": source.stone_id,
                        "case_external_id": source.case_external_id,
                    }
                    if source.kind == "observation"
                    else {}
                ),
            }
            for stone_id, sources in inputs.texts.items()
            for ref, source in sources.items()
            if source.text.strip()
        ],
        compatibility_targets={
            str(card.id): {
                build_pair_key(card.stone_type, stone_type): stone_type
                for stone_type in inputs.targets
            }
            for card in inputs.cards
        },
    )


async def _assess_candidates(
    inputs: CandidateEvaluationInputs, runtime: Runtime[RunContext]
) -> CandidateAssessmentResult:
    evidence = CandidateEvidence(character=[], individual_compatibility=[])
    status: AssessmentStatus = "not_needed"
    output_method: str | None = None
    model_details: dict[str, object] = {}
    criteria = inputs.criteria
    if criteria is None or not inputs.cards or not (inputs.character or inputs.targets):
        return CandidateAssessmentResult(evidence, status, output_method, model_details)

    status = "invalid_response"
    output_method, model = structured_model(
        runtime.context.models.evaluation_model,
        CandidateEvidence,
        use_json_schema=runtime.context.models.evaluation_uses_json_schema,
        reasoning=runtime.context.models.evaluation_reasoning,
    )
    response = await model.ainvoke(_candidate_evidence_messages(inputs), config=get_config())
    if not isinstance(response, dict):
        return CandidateAssessmentResult(evidence, status, output_method, model_details)
    raw = response.get("raw")
    parsed = response.get("parsed")
    if not isinstance(raw, AIMessage):
        return CandidateAssessmentResult(evidence, status, output_method, model_details)
    model_details = model_call_details(raw)
    if raw.response_metadata.get("finish_reason") == "length":
        return CandidateAssessmentResult(evidence, status, output_method, model_details)
    if not isinstance(parsed, CandidateEvidence):
        status = assessment_failure_status(response.get("parsing_error"))
        return CandidateAssessmentResult(evidence, status, output_method, model_details)
    if not _candidate_criteria_bindings_valid(parsed, criteria):
        status = "invalid_criterion_binding"
        return CandidateAssessmentResult(evidence, status, output_method, model_details)
    return CandidateAssessmentResult(parsed, "parsed", output_method, model_details)


def _candidate_criteria_bindings_valid(
    assessment: CandidateEvidence, criteria: SearchCriteria
) -> bool:
    criterion_fragments = {
        item.criterion_id: item.fragment_id
        for group in (criteria.requirements, criteria.preferences)
        for item in group.character
    }
    return all(
        criterion_fragments.get(item.criterion_id) == item.fragment_id
        for item in assessment.character
    )


def _candidate_evaluation_sources(
    inputs: CandidateEvaluationInputs, runtime: Runtime[RunContext]
) -> dict[str, dict[str, object]]:
    return {
        **{
            pair.source_key: {
                "tool": runtime.context.tools.compatibility_tool.name,
                "data": pair.model_dump(mode="json"),
            }
            for pair in inputs.pairs.values()
            if pair is not None
        },
        **{
            chapter.source_key: {
                "tool": runtime.context.tools.encyclopedia_tool.name,
                "data": chapter.model_dump(mode="json"),
            }
            for chapter in inputs.encyclopedia.values()
        },
        **{
            source.source_id: {
                "tool": runtime.context.tools.timeline_tool.name,
                "data": {
                    "event_external_id": source.event_external_id,
                    "event_type": source.event_type,
                    "occurred_at": source.occurred_at,
                    "stone_id": source.stone_id,
                    "case_external_id": source.case_external_id,
                    "event_notes": source.text,
                },
            }
            for sources in inputs.texts.values()
            for source in sources.values()
            if source.kind == "observation"
        },
    }


# Renders decisions from graph state and lets the model explain grounded candidates.
async def answer(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
    inputs = _prepare_candidate_answer_inputs(state, runtime)
    explanations, model_details = await _generate_candidate_explanations(state, runtime, inputs)
    sources = _candidate_answer_sources(inputs, explanations, runtime)
    decisions, lines, fallback_source_ids = _render_candidate_decisions(
        inputs, explanations
    )
    sources.update(
        (source_id, inputs.evaluation_sources[source_id])
        for source_id in fallback_source_ids
        if source_id in inputs.evaluation_sources
    )
    result: dict[str, object] = {
        "answer": "\n\n".join(lines)
        if lines
        else state.get("selection_note", "No checked candidates."),
        "sources": sources,
        "verified_statuses": inputs.statuses,
        "recommended_stone_ids": inputs.recommendations,
        "candidate_decisions": decisions,
        "question": state["question"],
        "question_fragments": state.get("question_fragments", {}),
        "candidate_status": state.get("assessment_status", "unknown"),
    }
    reference = state.get("reference_component")
    if reference is not None:
        result = combine_mixed_result(
            result, reference, state.get("reference_answer_status", "unknown")
        )
    return {
        "result": result,
        "model_call": model_details,
    }


def _prepare_candidate_answer_inputs(
    state: SearchState, runtime: Runtime[RunContext]
) -> CandidateAnswerInputs:
    cards = state.get("candidate_cards", {})
    card_sources: dict[str, dict[str, object]] = {
        f"stone-card:{stone_id}": {"tool": runtime.context.tools.details_tool.name, "data": card}
        for stone_id, card in cards.items()
    }
    evaluation_sources = state.get("evaluation_sources", {})
    evidence = {**card_sources, **evaluation_sources}
    evaluations = {
        item.stone_id: item
        for value in state.get("candidate_evaluations", [])
        if (item := CandidateEvaluation.model_validate(value)).stone_id in cards
    }
    recommendations = state.get("recommended_stone_ids", [])
    explainable = {
        stone_id: item
        for stone_id, item in evaluations.items()
        if item.outcome in {"recommended", "facts_only"}
    }
    allowed_evidence_ids = {
        stone_id: candidate_explanation_evidence_ids(stone_id, item, evidence)
        for stone_id, item in explainable.items()
    }
    return CandidateAnswerInputs(
        cards=cards,
        card_sources=card_sources,
        evaluation_sources=evaluation_sources,
        evidence=evidence,
        statuses=state.get("verified_statuses", {}),
        recommendations=recommendations,
        evaluations=evaluations,
        ordered_ids=dict.fromkeys(
            [*(stone_id for stone_id in recommendations if stone_id in evaluations), *evaluations]
        ),
        explainable=explainable,
        allowed_evidence_ids=allowed_evidence_ids,
    )


async def _generate_candidate_explanations(
    state: SearchState,
    runtime: Runtime[RunContext],
    inputs: CandidateAnswerInputs,
) -> tuple[dict[str, CandidateExplanation], dict[str, object]]:
    if not inputs.explainable:
        return {}, {}
    model = runtime.context.models.answer_model.with_structured_output(
        AnswerDraft, method="function_calling", include_raw=True, reasoning={"enabled": False}
    )
    response = await model.ainvoke(
        build_answer_messages(
            question=state["question"],
            candidates={
                stone_id: {
                    "name": inputs.cards[stone_id]["name"],
                    "allowed_evidence_ids": inputs.allowed_evidence_ids[stone_id],
                    "findings": [
                        reason.model_dump(mode="json")
                        for reason in item.reasons
                        if reason.criterion != "availability"
                    ],
                }
                for stone_id, item in inputs.explainable.items()
            },
            evidence={
                **{
                    f"stone-card:{stone_id}": {
                        key: value
                        for key, value in inputs.cards[stone_id].items()
                        if key != "shelter_case"
                    }
                    for stone_id in inputs.explainable
                },
                **inputs.evaluation_sources,
            },
        ),
        config=get_config(),
    )
    if not isinstance(response, dict) or not isinstance(raw := response.get("raw"), AIMessage):
        return {}, {}
    model_details = model_call_details(raw)
    draft = response.get("parsed")
    if raw.response_metadata.get("finish_reason") == "length" or not isinstance(
        draft, AnswerDraft
    ):
        return {}, model_details
    return _validate_candidate_explanations(draft, inputs), model_details


def _validate_candidate_explanations(
    draft: AnswerDraft, inputs: CandidateAnswerInputs
) -> dict[str, CandidateExplanation]:
    proposed_by_stone: dict[str, list[CandidateExplanation]] = {}
    for explanation in draft.explanations:
        if explanation.stone_id in inputs.explainable:
            proposed_by_stone.setdefault(explanation.stone_id, []).append(explanation)
    return {
        stone_id: proposed[0]
        for stone_id, proposed in proposed_by_stone.items()
        if len(proposed) == 1
        and proposed[0].explanation.strip()
        and proposed[0].evidence_ids
        and all(
            source_id in inputs.allowed_evidence_ids[stone_id]
            for source_id in proposed[0].evidence_ids
        )
    }


def _candidate_answer_sources(
    inputs: CandidateAnswerInputs,
    explanations: dict[str, CandidateExplanation],
    runtime: Runtime[RunContext],
) -> dict[str, dict[str, object]]:
    sources = {
        evidence_id: inputs.evidence[evidence_id]
        for explanation in explanations.values()
        for evidence_id in explanation.evidence_ids
        if evidence_id in inputs.evidence
    }
    sources.update(inputs.card_sources)
    sources.update(
        (source_id, source)
        for source_id, source in inputs.evaluation_sources.items()
        if source["tool"] == runtime.context.tools.compatibility_tool.name
    )
    used_observation_sources = {
        evidence.source_id
        for candidate in inputs.evaluations.values()
        for reason in candidate.reasons
        for evidence in reason.evidence
        if evidence.source_kind == "observation"
    }
    sources.update(
        (source_id, source)
        for source_id, source in inputs.evaluation_sources.items()
        if source_id in used_observation_sources
    )
    return sources


def _render_candidate_decisions(
    inputs: CandidateAnswerInputs,
    explanations: dict[str, CandidateExplanation],
) -> tuple[list[dict[str, object]], list[str], set[str]]:
    decisions: list[dict[str, object]] = []
    lines: list[str] = []
    fallback_source_ids: set[str] = set()
    for stone_id in inputs.ordered_ids:
        item = inputs.evaluations[stone_id]
        name = str(inputs.cards[stone_id]["name"])
        status = inputs.statuses.get(stone_id)
        decisions.append(
            {
                "stone_id": stone_id,
                "name": name,
                "adoption_status": status,
                "outcome": item.outcome,
                "rank": item.ranking.rank if item.ranking is not None else None,
                "exclusion_rules": item.exclusion_rules,
            }
        )
        lines.append(
            _render_candidate_line(
                item,
                name,
                status,
                explanations.get(stone_id),
                inputs.evaluation_sources,
                fallback_source_ids,
            )
        )
    return decisions, lines, fallback_source_ids


def _render_candidate_line(
    item: CandidateEvaluation,
    name: str,
    status: str | None,
    explanation: CandidateExplanation | None,
    evaluation_sources: dict[str, dict[str, object]],
    fallback_source_ids: set[str],
) -> str:
    labels = [status or "UNKNOWN", item.outcome, *item.exclusion_rules]
    labels.extend(dict.fromkeys(reason.verdict.value for reason in item.reasons if reason.verdict))
    line = f"**{name}** · " + " · ".join(f"`{label}`" for label in labels)
    if any(reason.conditions_status in {"unconfirmed", "unmarked"} for reason in item.reasons):
        line += "\nConditions are not confirmed."
    if explanation:
        line += f"\n{explanation.explanation}"
    elif item.outcome in {"excluded", "conditional_option"}:
        line += _render_unmet_reasons(item)
    if not explanation and item.outcome in {"recommended", "facts_only"}:
        line += _render_evidence_fallback(item, fallback_source_ids)
    line += _render_compatibility_reasons(item, evaluation_sources)
    return line


def _render_unmet_reasons(item: CandidateEvaluation) -> str:
    return "".join(
        f"\n- {reason.question_quote} · `{reason.finding}`"
        for reason in item.reasons
        if reason.criterion != "compatibility"
        and reason.question_quote
        and reason.finding != "confirmed"
    )


def _render_evidence_fallback(
    item: CandidateEvaluation, fallback_source_ids: set[str]
) -> str:
    lines = []
    for reason in item.reasons:
        if reason.criterion == "availability":
            continue
        for evidence in reason.evidence:
            if evidence.quote:
                lines.append(
                    f"\n- {reason.question_quote or reason.criterion} · "
                    f"[{evidence.finding}] · {evidence.quote} · [{evidence.source_id}]"
                )
                fallback_source_ids.add(evidence.source_id)
    return "".join(lines)


def _render_compatibility_reasons(
    item: CandidateEvaluation, evaluation_sources: dict[str, dict[str, object]]
) -> str:
    lines = []
    for reason in item.reasons:
        if reason.criterion != "compatibility" or not reason.pair_key:
            continue
        verdict = reason.verdict.value if reason.verdict else "UNKNOWN"
        line = f"\n- {reason.pair_key} · `{verdict}` · `{reason.finding}`"
        if reason.conditions_status:
            line += f" · conditions: `{reason.conditions_status}`"
        pair_source = evaluation_sources.get(reason.source_id or "")
        if pair_source:
            pair = CompatibilityPairSearchDocument.model_validate(pair_source["data"])
            line += "\n" + "\n".join(f"  > {part}" for part in pair.text.splitlines())
        lines.append(line)
    return "".join(lines)


# Builds the final payload when a budget reservation is refused.
# Returns the reason from the graph state and an empty recommendation list.
def stop(state: SearchState) -> dict[str, object]:
    result: dict[str, object] = {
        "answer": "The workflow stopped at a configured limit.",
        "stop_reason": state["stop_reason"],
        "recommended_stone_ids": [],
        "candidate_decisions": [],
    }
    if (reference := state.get("reference_component")) is not None:
        result = combine_mixed_result(
            result, reference, state.get("reference_answer_status", "unknown")
        )
        result["candidate_branch_status"] = state["stop_reason"]
    elif (reference_result := state.get("reference_result")) is not None:
        lines = list(reference_result.lines)
        for source in reference_result.context_sources.values():
            lines.append(f"**{SCOPE_TITLES[source.scope]}** · {source.source_id}\n{source.text}")
        reference_payload: dict[str, object] = {
            "answer": "\n\n".join(lines)
            or "Reference sources were read, but no answer summary was produced.",
            "sources": reference_result.sources,
            "verified_statuses": (
                {str(reference_result.stone.stone_id): reference_result.stone.adoption_status.value}
                if reference_result.stone
                else {}
            ),
        }
        result = combine_mixed_result(result, reference_payload, "summary_not_reached")
        result["candidate_branch_status"] = state["stop_reason"]
    return {
        "result": result,
    }


# Runs a model stage through the budget interface and returns its state updates.
# The budget currently admits calls while OpenRouter reports the real usage separately.
def with_model_budget(node: WorkflowNode) -> WorkflowNode:
    async def run(state: SearchState, *, runtime: Runtime[RunContext]) -> dict[str, object]:
        budget = runtime.context.budget
        if not budget.try_reserve(PLACEHOLDER_RESERVE):
            return {"stop_reason": "budget_limit"}

        return await node(state, runtime=runtime)

    return run


# Routing


def after_selection(state: SearchState) -> Literal["stop", "read_candidate_cards"]:
    return "stop" if state.get("stop_reason") else "read_candidate_cards"


def after_parsing(state: SearchState) -> Literal["stop", "ground_question"]:
    return "stop" if state.get("stop_reason") else "ground_question"


def after_planning(
    state: SearchState,
) -> Literal["stop", "clarify_request", "search_candidates", "execute_reference_plan"]:
    if state.get("stop_reason"):
        return "stop"
    if state.get("plan_status") != "accepted":
        return "clarify_request"
    if "search_candidates" in state["tool_plan"].tools and len(state["tool_plan"].tools) == 1:
        return "search_candidates"
    return "execute_reference_plan"


# Stops on a refused evaluation budget or continues to answer.
def after_evaluation(state: SearchState) -> Literal["stop", "answer"]:
    return "stop" if state.get("stop_reason") else "answer"


# Reads the stop reason and returns stop for a refused answer budget.
# Otherwise returns done, which the graph maps to END.
def after_answer(state: SearchState) -> Literal["stop", "done"]:
    return "stop" if state.get("stop_reason") else "done"
