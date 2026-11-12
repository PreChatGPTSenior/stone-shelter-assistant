"""Run the actual graph with fixture models and in-memory telemetry only."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langfuse import Langfuse
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from tests.unit.search.test_rrf import card

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_evaluation import (
    CandidateEvidence,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.question_grounding import (
    GroundingDecision,
    GroundingResponse,
)
from stone_shelter_assistant.assistant.reference_evidence import (
    ReferenceAnswer,
    ReferenceEvidence,
    ReferenceQuote,
    ReferenceSection,
)
from stone_shelter_assistant.assistant.reference_lookup import ReferenceResult, ReferenceTools
from stone_shelter_assistant.assistant.selection import (
    ParseQuestion,
    RetrievalRequest,
    SelectCandidates,
)
from stone_shelter_assistant.assistant.tool_planning import ReferenceRequest, ToolPlan
from stone_shelter_assistant.assistant.tools import stone_search_tools
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.search.knowledge.grounding_catalog import (
    GroundingEntry,
    build_grounding_snapshot,
)
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneType
from stone_shelter_assistant.stones.stone_contracts import NamedStoneStatus, StoneDetails


def payload(span: Any, field: str) -> Any:
    return json.loads(span.attributes[f"langfuse.observation.{field}"])


@pytest.mark.asyncio
@pytest.mark.parametrize("current_status", ["AVAILABLE", "RESERVED"])
async def test_full_hybrid_graph_preserves_provenance_and_decisions(current_status: str) -> None:
    snapshot = json.loads(
        (Path(__file__).parents[1] / "fixtures/assistant/quiet-home-assessment.json").read_text()
    )
    details: dict[str, Any] = next(
        item for item in snapshot["cards"] if item["name"] == "Sir Pebble"
    )
    reference_details: dict[str, Any] = next(
        item for item in snapshot["cards"] if item["name"] == "Madame Obsidian"
    )
    sid = details["id"]
    a = card(1).model_copy(
        update={
            "id": UUID(sid),
            "stone_external_id": UUID(details["external_id"]),
            "title": details["name"],
            "text": details["biography"],
        }
    )
    b = card(2)
    documents = SimpleNamespace(
        search=AsyncMock(
            return_value={"hits": [{"document": item.model_dump(mode="json")} for item in (a, b)]}
        )
    )
    typesense: Any = SimpleNamespace(collections={"stones": SimpleNamespace(documents=documents)})
    qdrant: Any = SimpleNamespace(
        query_points=AsyncMock(
            return_value=SimpleNamespace(
                points=[
                    SimpleNamespace(id=str(item.id), payload=item.model_dump(mode="json"))
                    for item in (b, a)
                ]
            )
        )
    )
    embeddings: Any = SimpleNamespace(
        model="fixture-embedding", aembed_query=AsyncMock(return_value=[1.0])
    )
    search = StoneSearchService(typesense, qdrant, embeddings)
    search_tools = stone_search_tools(search, AsyncMock())

    @tool
    async def get_stone_details(stone_id: str) -> dict[str, Any]:
        """Read the authoritative fixture card."""
        assert stone_id == sid
        return details

    @tool
    async def get_reference_status_by_name(name: str) -> list[dict[str, str]]:
        """Read the named reference individual's current status."""
        assert name == "Madame Obsidian"
        return [
            {
                "stone_id": reference_details["id"],
                "name": name,
                "stone_type": "OBSIDIAN",
                "adoption_status": "AVAILABLE",
            }
        ]

    @tool
    async def get_reference_details(stone_id: str) -> dict[str, Any]:
        """Read the named reference individual's profile."""
        assert stone_id == reference_details["id"]
        return reference_details

    @tool
    async def get_current_stone_statuses(stone_ids: list[str]) -> list[dict[str, str]]:
        """Read the fixture's current availability."""
        return [
            {
                "stone_id": item,
                "adoption_status": current_status,
                "current_shelter_id": str(UUID(int=300)),
            }
            for item in stone_ids
        ]

    @tool
    async def get_case_timeline(case_external_id: str) -> list[dict[str, str]]:
        """Read candidate history; this fixture has no relevant events."""
        return []

    @tool
    async def get_compatibility_pair(first_type: str, second_type: str) -> None:
        """No pair was requested in this scenario."""
        raise AssertionError("Unexpected pair lookup")

    @tool
    async def search_knowledge_lexical(filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        """No general character evidence is needed for this fixture."""
        return []

    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requested_availability": [],
            "requested_compatibility": [],
            "household_facts": [
                {"fragment_id": 1, "fact_type": "decision_rotation_agreed", "value": False}
            ],
            "requirements": {"character": [{"fragment_id": 1}], "compatibility": []},
            "preferences": {"character": [], "compatibility": []},
            "retrieval": {
                "lexical_query": "quiet evenings",
                "semantic_query": "quiet home",
                "candidate_type": None,
            },
            "named_stone": {"fragment_id": 1, "name": "Madame Obsidian"},
            "requested_stone_info": {"fragment_id": 1, "topic": "preferences"},
        }
    )
    from stone_shelter_assistant.assistant.tool_planning import permitted_tools

    parsed_criteria, _ = parsed.resolve(
        {1: "Tell me what Madame Obsidian likes and find one quiet stone."}
    )
    parsed_reference = parsed.resolve_references(
        {1: "Tell me what Madame Obsidian likes and find one quiet stone."}
    )
    allowed_plan = permitted_tools(parsed_criteria, parsed_reference)
    outputs = {
        GroundingResponse: GroundingResponse(
            decisions=[
                GroundingDecision(
                    proposal_id="agreement:0",
                    finding="unknown",
                    fragment_id=1,
                    quote="Tell me what Madame Obsidian likes and find one quiet stone.",
                    reason="No agreement was stated.",
                )
            ]
        ),
        ParseQuestion: parsed,
        ToolPlan: ToolPlan(
            tools=allowed_plan, reason="Read the named profile and search candidates"
        ),
        SelectCandidates: SelectCandidates(stone_ids=[sid]),
        CandidateEvidence: CandidateEvidence.model_validate(
            {
                "character": [
                    {
                        "stone_id": sid,
                        "source_ref": "biography",
                        "finding": "confirmed",
                        "quote": "enjoys quiet evenings",
                        "fragment_id": 1,
                    }
                ],
                "individual_compatibility": [],
            }
        ),
        workflow.AnswerDraft: workflow.AnswerDraft(
            explanations=[
                workflow.CandidateExplanation(
                    stone_id=sid,
                    explanation="Enjoys quiet evenings.",
                    evidence_ids=[f"stone-card:{sid}"],
                )
            ]
        ),
    }

    class FixtureModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            if schema is ReferenceEvidence:

                async def evidence(messages: Any) -> dict[str, Any]:
                    sources = json.loads(messages[-1].content)["sources"]
                    return {
                        "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                        "parsed": ReferenceEvidence(
                            quotes=[
                                ReferenceQuote(source_id=s["source_id"], quote=s["text"])
                                for s in sources
                            ]
                        ),
                    }

                return RunnableLambda(evidence)
            if schema is ReferenceAnswer:

                def answer_reference(messages: Any) -> dict[str, Any]:
                    quotes = json.loads(messages[-1].content)["quotes"]
                    scope = quotes[0]["scope"]
                    return {
                        "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                        "parsed": ReferenceAnswer(
                            sections=[
                                ReferenceSection(
                                    scope=scope,
                                    explanation="Madame Obsidian enjoys a peaceful home.",
                                    source_ids=[q["source_id"] for q in quotes],
                                )
                            ]
                        ),
                    }

                return RunnableLambda(answer_reference)
            return RunnableLambda(
                lambda _: {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": outputs[schema],
                },
                name="fixture_model",
            )

    model: Any = FixtureModel()
    exporter = InMemorySpanExporter()
    public_key = f"test-{uuid4()}"
    client = Langfuse(
        public_key=public_key,
        secret_key="test-secret",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
    )
    try:
        with client.start_as_current_observation(name="questions") as root:
            callback = WorkflowTraceHandler(
                public_key=public_key,
                trace_context={"trace_id": root.trace_id, "parent_span_id": root.id},
            )
            result = await workflow.run_workflow(
                "Tell me what Madame Obsidian likes and find one quiet stone.",
                grounding_catalog=AsyncMock(
                    load=AsyncMock(
                        return_value=build_grounding_snapshot(
                            [
                                GroundingEntry.model_validate(e)
                                for e in json.loads(
                                    (
                                        Path(__file__).parents[2]
                                        / "fixtures/knowledge/grounding/grounding_en-v1.json"
                                    ).read_text()
                                )
                            ],
                            "en",
                            "en-v1",
                        )
                    )
                ),
                selection_model=model,
                selection_uses_json_schema=True,
                parsing_model=model,
                planning_model=model,
                evaluation_model=model,
                evaluation_uses_json_schema=True,
                answer_model=model,
                retrieval_tools=search_tools,
                details_tool=get_stone_details,
                status_tool=get_current_stone_statuses,
                timeline_tool=get_case_timeline,
                compatibility_tool=get_compatibility_pair,
                encyclopedia_tool=search_knowledge_lexical,
                reference_tools=ReferenceTools(
                    stone_status=get_reference_status_by_name,
                    stone_details=get_reference_details,
                    timeline=get_case_timeline,
                    encyclopedia=search_knowledge_lexical,
                    exact_pair=get_compatibility_pair,
                    pair_list=get_compatibility_pair,
                ),
                config={"callbacks": [callback], "run_name": "search-workflow"},
            )
        client.flush()
        spans = exporter.get_finished_spans()
        by_name = {span.name: span for span in spans}
        assert result["recommended_stone_ids"] == ([sid] if current_status == "AVAILABLE" else [])
        parse_output = payload(by_name["ground_question"], "output")
        assert parse_output["criteria"]["household_facts"] == []
        assert parse_output["parser_diagnostics"][0]["kind"] == "unsupported_agreement"
        assert parse_output["retrieval"]["filters"]["language"] == "en"
        decisions_output = result["candidate_decisions"]
        assert isinstance(decisions_output, list)
        assert decisions_output[0]["outcome"] == (
            "recommended" if current_status == "AVAILABLE" else "excluded"
        )
        assert result["reference_answer_status"] == "generated"
        answer_text = result["answer"]
        assert isinstance(answer_text, str)
        assert "Madame Obsidian enjoys a peaceful home." in answer_text
        if current_status == "AVAILABLE":
            assert "Enjoys quiet evenings." in answer_text
        verified_statuses = result["verified_statuses"]
        assert isinstance(verified_statuses, dict)
        assert verified_statuses[reference_details["id"]] == "AVAILABLE"
        assert verified_statuses[sid] == current_status
        sources = result["sources"]
        assert isinstance(sources, dict)
        assert f"stone-card:{reference_details['id']}" in sources
        assert len({span.context.trace_id for span in spans}) == 1
        for name in ("typesense_search", "qdrant_search", "rrf_fusion"):
            assert name in by_name
            parent = by_name[name].parent
            assert parent is not None
            assert parent.span_id == by_name["search_stones_hybrid"].context.span_id
        assert payload(by_name["qdrant_search"], "input")["embedding_model"] == "fixture-embedding"
        fused = payload(by_name["rrf_fusion"], "output")
        assert fused["lexical_ids"] == [sid, str(b.id)]
        assert fused["semantic_ids"] == [str(b.id), sid]
        tools_output = payload(by_name["tools"], "output")
        assert tools_output["tools_used"] == 2
        provenance = tools_output["retrieval_provenance"]
        hit = next(item for item in provenance if item["stone_id"] == sid)
        assert hit["lexical_rank"] == 1 and hit["semantic_rank"] == 2
        assert hit["rrf_score"] == pytest.approx(1 / 61 + 1 / 62)
        assert "Typesense #1" in hit["explanation"]
        decisions = payload(by_name["select_candidates"], "output")["selection_decisions"]
        assert {item["stone_id"]: item["selected"] for item in decisions} == {
            sid: True,
            str(b.id): False,
        }
        assert payload(by_name["verify"], "output")["verified_statuses"][sid] == current_status
        evaluation = payload(by_name["evaluate_candidates"], "output")["candidate_evaluations"][0]
        assert evaluation["stone_id"] == sid
        assert evaluation["eligible"] == (current_status == "AVAILABLE")
        assert not any(span.name.startswith(("Runnable", "after_")) for span in spans)
    finally:
        client.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "named,used,expected",
    [(False, 0, "search_stones_hybrid"), (True, 0, "search_stones_lexical"), (False, 3, None)],
)
async def test_retrieval_routes_and_two_call_allowance(
    named: bool, used: int, expected: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})

    @tool
    async def search_stones_hybrid(
        lexical_query: str, semantic_query: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Fixture hybrid search."""
        return {"candidates": [], "dropped": []}

    search_stones_hybrid.metadata = {"retrieval_calls": 2}

    @tool
    async def search_stones_lexical(query: str) -> list[dict[str, Any]]:
        """Fixture name search."""
        return []

    context: Any = SimpleNamespace(
        tool_executor=ToolNode([search_stones_hybrid, search_stones_lexical])
    )
    state: workflow.SearchState = {
        "question": "fixture",
        "messages": [],
        "tools_used": used,
        "reference_request": ReferenceRequest(
            stone_name="Sir Pebble" if named else None,
            recommendation_name="Sir Pebble" if named else None,
            care_types=[],
            pairs=[],
            pair_lists=[],
        ),
        "retrieval": RetrievalRequest.model_validate(
            {"lexical_query": "quiet", "semantic_query": "quiet home", "filters": {}}
        ),
    }
    result = await workflow.search_candidates(state, runtime=Runtime(context=context))
    if expected is None:
        assert result["stop_reason"] == "retrieval_call_limit"
        return
    messages = result["messages"]
    assert isinstance(messages, list)
    reply: Any = messages[0]
    assert reply.tool_calls[0]["name"] == expected
    state["messages"] = [reply]
    update = await workflow.tools(state, runtime=Runtime(context=context))
    assert update["tools_used"] == used + (1 if named else 2)


def test_collector_excludes_hits_dropped_by_fusion() -> None:
    state: workflow.SearchState = {
        "question": "fixture",
        "tools_used": 2,
        "messages": [
            ToolMessage(
                name="search_stones_hybrid",
                tool_call_id="search",
                content=json.dumps(
                    {
                        "candidates": [{"card": {"id": "kept"}}],
                        "dropped": [{"card": {"id": "dropped"}}],
                    }
                ),
            )
        ],
    }
    assert list(workflow.retrieved_candidates(state)) == ["kept"]


@pytest.mark.asyncio
async def test_named_recommendation_rejects_a_different_retrieved_stone_id() -> None:
    target_id = uuid4()
    other_id = uuid4()
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
        }
    )
    criteria, _ = parsed.resolve({1: "Recommend Svetlana."})
    request = parsed.resolve_references({1: "Recommend Svetlana."})

    class UnexpectedModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            raise AssertionError("Selection must stop before accepting a different stone ID.")

    state: workflow.SearchState = {
        "question": "Recommend Svetlana.",
        "tools_used": 1,
        "criteria": criteria,
        "reference_request": request,
        "reference_result": ReferenceResult(
            recommendation_stone=NamedStoneStatus(
                stone_id=target_id,
                name="Svetlana",
                stone_type=StoneType.MARBLE,
                adoption_status=AdoptionStatus.AVAILABLE,
            )
        ),
        "messages": [
            ToolMessage(
                name="search_stones_lexical",
                tool_call_id="search",
                content=json.dumps([{"id": str(other_id), "title": "Other stone"}]),
            )
        ],
    }
    context = SimpleNamespace(
        selection_model=UnexpectedModel(),
        selection_uses_json_schema=True,
    )
    result = await workflow.select_candidates(state, runtime=Runtime(context=cast(Any, context)))
    assert result["selected_stone_ids"] == []
    assert result["selection_status"] == "named_candidate_not_retrieved"
    assert "no substitute was selected" in str(result["selection_note"])


@pytest.mark.asyncio
async def test_named_recommendation_filters_model_selection_to_the_resolved_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    target_id = uuid4()
    other_id = uuid4()
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 2,
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
        }
    )
    criteria, _ = parsed.resolve({1: "Recommend Svetlana."})
    request = parsed.resolve_references({1: "Recommend Svetlana."})
    seen_cards: list[str] = []

    class FixtureModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def select(messages: Any) -> dict[str, Any]:
                seen_cards.extend(
                    item["id"] for item in json.loads(messages[-1].content)["retrieved_cards"]
                )
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": SelectCandidates(stone_ids=[str(target_id), str(other_id)]),
                }

            return RunnableLambda(select)

    state: workflow.SearchState = {
        "question": "Recommend Svetlana.",
        "tools_used": 1,
        "criteria": criteria,
        "reference_request": request,
        "reference_result": ReferenceResult(
            recommendation_stone=NamedStoneStatus(
                stone_id=target_id,
                name="Svetlana",
                stone_type=StoneType.MARBLE,
                adoption_status=AdoptionStatus.AVAILABLE,
            )
        ),
        "messages": [
            ToolMessage(
                name="search_stones_lexical",
                tool_call_id="search",
                content=json.dumps(
                    [
                        {"id": str(target_id), "title": "Svetlana"},
                        {"id": str(other_id), "title": "Other stone"},
                    ]
                ),
            )
        ],
    }
    result = await workflow.select_candidates(
        state,
        runtime=Runtime(
            context=cast(
                Any,
                SimpleNamespace(
                    selection_model=FixtureModel(),
                    selection_uses_json_schema=True,
                ),
            )
        ),
    )
    assert seen_cards == [str(target_id)]
    assert result["selected_stone_ids"] == [str(target_id)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("issue", "message"),
    [("not_found", "No stone was found"), ("ambiguous", "matches multiple stones")],
)
async def test_named_recommendation_does_not_select_when_name_is_not_unique(
    issue: str, message: str
) -> None:
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
        }
    )
    criteria, _ = parsed.resolve({1: "Recommend Svetlana."})
    state: workflow.SearchState = {
        "question": "Recommend Svetlana.",
        "tools_used": 1,
        "criteria": criteria,
        "reference_request": parsed.resolve_references({1: "Recommend Svetlana."}),
        "reference_result": ReferenceResult(recommendation_issue=issue),
        "messages": [],
    }
    result = await workflow.select_candidates(
        state,
        runtime=Runtime(
            context=cast(
                Any,
                SimpleNamespace(
                    selection_model=SimpleNamespace(),
                    selection_uses_json_schema=True,
                ),
            )
        ),
    )
    assert result["selected_stone_ids"] == []
    assert message in str(result["selection_note"])


@pytest.mark.asyncio
@pytest.mark.parametrize("compatibility_only", [False, True])
async def test_candidate_assessment_loads_svetlana_observations_with_event_provenance(
    monkeypatch: pytest.MonkeyPatch, compatibility_only: bool
) -> None:
    fixture = json.loads(
        (
            Path(__file__).parents[2] / "fixtures/stones/b19266ec-28a2-4fd3-851b-7fad50b6e175.json"
        ).read_text()
    )
    case = fixture["shelterCase"]
    stone = fixture["stone"]
    profile = fixture["profile"]
    card = StoneDetails.model_validate(
        {
            "id": str(UUID(int=501)),
            "external_id": stone["externalId"],
            "name": stone["name"],
            "stone_type": stone["stoneType"],
            "stone_size": stone["stoneSize"],
            "biography": stone["biography"],
            "profile": {
                "socialization_traits": [],
                "care_level": None,
                "health_notes": None,
                "trigger_notes": None,
                "preferred_environment": profile["preferredEnvironment"],
            },
            "shelter_case": {
                "id": str(UUID(int=502)),
                "external_id": case["externalId"],
                "case_number": case["caseNumber"],
                "adoption_status": case["adoptionStatus"],
                "current_shelter_id": case["currentShelterId"],
                "admission_date": case["admissionDate"],
            },
        }
    )
    events = [
        {
            "event_external_id": event["externalId"],
            "event_type": event["eventType"],
            "occurred_at": event["occurredAt"],
            "event_notes": event["eventNotes"],
        }
        for event in case["events"]
    ]

    @tool
    async def timeline(case_external_id: str) -> list[dict[str, str]]:
        """Read the case timeline from its external ID."""
        assert case_external_id == case["externalId"]
        return events

    event_findings = [
        {
            "stone_id": str(card.id),
            "fragment_id": 1,
            "source_ref": "observation",
            "observation_external_id": event["event_external_id"],
            "finding": "contradicted",
            "quote": (
                "sings loudly on the windowsill every morning at 05:00"
                if event["event_type"] == "OBSERVATION"
                and "staff observed" in event["event_notes"].casefold()
                else "disturbed the neighbors"
                if "First neighbor complaint" in event["event_notes"]
                else "neighbors objected to the early-morning noise"
            ),
        }
        for event in events
        if event["event_type"] == "OBSERVATION"
    ]
    assessment = CandidateEvidence.model_validate(
        {
            "character": []
            if compatibility_only
            else [
                *event_findings,
                {
                    "stone_id": str(card.id),
                    "fragment_id": 1,
                    "source_ref": "biography",
                    "finding": "contradicted",
                    "quote": "loves singing loudly on a windowsill, especially early in the morning",
                },
            ],
            "individual_compatibility": [],
        }
    )
    evaluation_model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={
                "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                "parsed": assessment,
            }
        )
    )
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    monkeypatch.setattr(workflow, "load_compatibility_pairs", AsyncMock(return_value={}))
    monkeypatch.setattr(workflow, "load_encyclopedia", AsyncMock(return_value={}))
    monkeypatch.setattr(
        workflow, "structured_model", lambda *args, **kwargs: ("json_schema", evaluation_model)
    )
    criteria = SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [],
            "requirements": {
                "character": []
                if compatibility_only
                else [{"fragment_id": 1, "question_quote": "Must stay quiet in the morning."}],
                "compatibility": [],
            },
            "preferences": {
                "character": [],
                "compatibility": [
                    {
                        "fragment_id": 1,
                        "question_quote": "Ideally compatible with granite.",
                        "household_type": "GRANITE",
                    }
                ]
                if compatibility_only
                else [],
            },
        }
    )
    runtime = Runtime(
        context=cast(
            workflow.RunContext,
            SimpleNamespace(
                compatibility_tool=None,
                encyclopedia_tool=None,
                timeline_tool=timeline,
                evaluation_model=None,
                evaluation_uses_json_schema=True,
                evaluation_reasoning=None,
            ),
        )
    )
    state: workflow.SearchState = {
        "question": "Find stones suitable for a quiet morning.",
        "messages": [],
        "tools_used": 1,
        "criteria": criteria,
        "criteria_status": "parsed",
        "candidate_cards": {str(card.id): card.model_dump(mode="json")},
        "verified_statuses": {str(card.id): "AVAILABLE"},
    }
    result = await workflow.evaluate_candidates(
        state,
        runtime=runtime,
    )
    sources = cast(dict[str, dict[str, object]], result["evaluation_sources"])
    for event in events:
        if event["event_type"] != "OBSERVATION":
            continue
        source_id = f"case-event:{event['event_external_id']}"
        source_data = cast(dict[str, str], sources[source_id]["data"])
        assert {key: source_data[key] for key in event} == event
        assert source_data["stone_id"] == str(card.id)
        assert source_data["case_external_id"] == case["externalId"]
    payload = json.loads(evaluation_model.ainvoke.call_args.args[0][1].content)
    observation_records = [
        source for source in payload["candidate_sources"] if source["source_ref"] == "observation"
    ]
    assert len(observation_records) == 3
    assert {source["observation_external_id"] for source in observation_records} == {
        event["event_external_id"] for event in events if event["event_type"] == "OBSERVATION"
    }
    if compatibility_only:
        assert result["assessment_status"] == "parsed"
        return
    decision = cast(list[dict[str, object]], result["candidate_evaluations"])[0]
    reasons = cast(list[dict[str, object]], decision["reasons"])
    character = next(reason for reason in reasons if reason["criterion"] == "character")
    evidence = cast(list[dict[str, object]], character["evidence"])
    assert character["finding"] == "contradicted"
    assert {item["source_id"] for item in evidence} >= {
        f"case-event:{event['event_external_id']}"
        for event in events
        if event["event_type"] == "OBSERVATION"
    }
    assert decision["outcome"] == "excluded"
    answer_state: workflow.SearchState = {
        "question": "Find stones suitable for a quiet morning.",
        "messages": [],
        "tools_used": 2,
        "criteria": criteria,
        "criteria_status": "parsed",
        "candidate_cards": {str(card.id): card.model_dump(mode="json")},
        "verified_statuses": {str(card.id): "AVAILABLE"},
        "recommended_stone_ids": [],
        "candidate_evaluations": cast(list[dict[str, object]], result["candidate_evaluations"]),
        "evaluation_sources": sources,
    }
    answer_runtime = Runtime(
        context=cast(
            workflow.RunContext,
            SimpleNamespace(
                details_tool=SimpleNamespace(name="get_stone_details"),
                compatibility_tool=SimpleNamespace(name="get_compatibility_pair"),
                answer_model=None,
                evaluation_reasoning=None,
            ),
        )
    )
    answer_result = await workflow.answer(answer_state, runtime=answer_runtime)
    answer_sources = cast(
        dict[str, dict[str, object]], cast(dict[str, object], answer_result["result"])["sources"]
    )
    assert {
        f"case-event:{event['event_external_id']}"
        for event in events
        if event["event_type"] == "OBSERVATION"
    } <= set(answer_sources)
