"""Semantic-verifier contracts with fixture decisions; not a model-quality claim."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.runtime import Runtime
from pydantic import ValidationError
from tests.evaluation.grounding_cases import parsed_grounding_case
from tests.integration.test_grounding_model_evaluation import grounding_metrics

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.question_grounding import (
    GroundingDecision,
    GroundingResponse,
    QuestionCoverageAudit,
    QuestionCoverageIssue,
    validate_grounding_response,
    validate_question_coverage,
)
from stone_shelter_assistant.assistant.reference_lookup import ReferenceResult
from stone_shelter_assistant.assistant.selection import (
    ParseQuestion,
    RetrievalProposal,
    question_fragments,
    validate_parsed_atoms,
)
from stone_shelter_assistant.search.knowledge.grounding_catalog import (
    GroundingEntry,
    build_grounding_snapshot,
)

ROOT = Path(__file__).parents[2]
HOLDOUT = json.loads((ROOT / "tests/fixtures/agent-eval/grounding-en/holdout.json").read_text())


def false_refusal_inputs() -> list[tuple[str, str, dict[str, Any]]]:
    """Current-contract interpretations of five PY-050 false-refusal questions."""
    cases = [
        (
            "Q02",
            "Find up to two stones for a quiet home where a granite stone already lives. "
            "Who is currently available and why might they fit?",
            {
                "recommendation_limit": 2,
                "household_facts": [
                    {
                        "fragment_id": 1,
                        "question_quote": "a granite stone already lives",
                        "existing_stone_type": "GRANITE",
                    }
                ],
                "requirements": {
                    "character": [{"fragment_id": 1, "question_quote": "for a quiet home"}]
                },
                # Exact same-source overlap follows the resolver's required precedence.
                "preferences": {
                    "character": [{"fragment_id": 1, "question_quote": "for a quiet home"}]
                },
                "retrieval": {
                    "lexical_query": "quiet home stones",
                    "semantic_query": "Stones suited to a quiet home with granite already living there.",
                },
            },
        ),
        (
            "Q09",
            "Find one obsidian stone. The stone must tolerate a vacuum cleaner calmly because we use it daily. "
            "Enjoying human company is a preference, not a requirement.",
            {
                "recommendation_limit": 1,
                "requirements": {
                    "character": [
                        {
                            "fragment_id": 2,
                            "question_quote": "tolerate a vacuum cleaner calmly",
                        }
                    ]
                },
                "preferences": {
                    "character": [
                        {"fragment_id": 3, "question_quote": "Enjoying human company"}
                    ]
                },
                "retrieval": {
                    "lexical_query": "obsidian vacuum calm human company",
                    "semantic_query": "An obsidian stone calm around a frequently used vacuum cleaner, preferably sociable.",
                    "candidate_type": {"fragment_id": 1, "stone_type": "OBSIDIAN"},
                },
            },
        ),
        (
            "Q10",
            "Find one gneiss stone for a family with children. Being good with children is required. "
            "Enjoying garden visits is only a preference.",
            {
                "recommendation_limit": 1,
                "requirements": {
                    "character": [
                        {"fragment_id": 2, "question_quote": "Being good with children"}
                    ]
                },
                "preferences": {
                    "character": [
                        {"fragment_id": 3, "question_quote": "Enjoying garden visits"}
                    ]
                },
                "retrieval": {
                    "lexical_query": "gneiss children garden",
                    "semantic_query": "A gneiss stone suited to a family with children, preferably enjoying garden visits.",
                    "candidate_type": {"fragment_id": 1, "stone_type": "GNEISS"},
                },
            },
        ),
        (
            "Q11",
            "Find one slate stone for a home with loud music. Calm behavior around music is required. "
            "I have caregiving experience.",
            {
                "recommendation_limit": 1,
                "household_facts": [
                    {"fragment_id": 1, "question_quote": "a home with loud music"}
                ],
                "requirements": {
                    "character": [
                        {"fragment_id": 2, "question_quote": "Calm behavior around music"}
                    ]
                },
                "retrieval": {
                    "lexical_query": "slate calm loud music",
                    "semantic_query": "A slate stone that stays calm around loud music.",
                    "candidate_type": {"fragment_id": 1, "stone_type": "SLATE"},
                },
            },
        ),
        (
            "Q16",
            "Find one pumice stone for a home where granite already lives. Is enjoying the company of "
            "other stones enough to prove compatibility with granite?",
            {
                "recommendation_limit": 1,
                "household_facts": [
                    {"fragment_id": 1, "question_quote": "granite already lives", "existing_stone_type": "GRANITE"}
                ],
                "requested_compatibility": [
                    {
                        "fragment_id": 2,
                        "household_type": "GRANITE",
                        "target": "candidate",
                    }
                ],
                "retrieval": {
                    "lexical_query": "pumice stone granite",
                    "semantic_query": "A pumice stone for a home with granite; the question asks whether general sociability proves compatibility.",
                    "candidate_type": {"fragment_id": 1, "stone_type": "PUMICE"},
                },
            },
        ),
    ]
    return cases


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "question", "fields"),
    false_refusal_inputs(),
    ids=[case[0] for case in false_refusal_inputs()],
)
async def test_schema_aware_audit_accepts_current_parse_for_contextual_questions(
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    question: str,
    fields: dict[str, Any],
) -> None:
    """Contract test for five PY-050 false refusals; it does not assess model quality."""
    parsed = ParseQuestion.model_validate(fields)
    fragments = question_fragments(question)
    proposals = parsed.grounding_proposals(fragments)
    payloads: list[dict[str, Any]] = []

    class Model:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            assert schema is GroundingResponse

            def respond(messages: Any) -> dict[str, Any]:
                payload = json.loads(messages[-1].content)
                payloads.append(payload)
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": GroundingResponse(
                        decisions=[
                            GroundingDecision(
                                proposal_id=proposal.proposal_id,
                                finding="supported",
                                fragment_id=proposal.fragment_id,
                                quote=proposal.question_quote,
                                reason="The exact proposal is supported in its source text.",
                            )
                            for proposal in proposals
                        ],
                        question_coverage=QuestionCoverageAudit(
                            status="complete",
                            summary="Independent requests and criteria are represented by the typed parse.",
                        ),
                    ),
                }

            return RunnableLambda(respond)

    monkeypatch.setattr(workflow, "get_config", lambda: {})
    context: Any = SimpleNamespace(
        grounding_catalog=AsyncMock(load=AsyncMock(return_value=snapshot())),
        evaluation_model=Model(),
        evaluation_uses_json_schema=True,
        evaluation_reasoning=None,
    )
    grounded: Any = await workflow.ground_question(
        {
            "question": question,
            "question_fragments": fragments,
            "parsed_question": parsed,
            "messages": [],
            "tools_used": 0,
        },
        runtime=Runtime(context=context),
    )

    assert grounded["question_coverage_status"] == "complete", case_id
    assert grounded["criteria_status"] == "parsed", case_id
    assert len(payloads) == 1
    schema = payloads[0]["parse_schema"]
    assert schema == ParseQuestion.model_json_schema()
    limit_description = schema["properties"]["recommendation_limit"]["description"]
    assert "recommendation action and requested quantity" in limit_description
    assert "explain why a recommended stone fits" in limit_description
    availability_description = schema["properties"]["requested_availability"]["description"]
    assert "Recommendations already use AVAILABLE retrieval" in availability_description
    household_description = schema["$defs"]["HouseholdFactReference"]["properties"][
        "existing_stone_type"
    ]["description"]
    assert "presence alone is not a compatibility requirement or preference" in household_description
    compatibility_description = schema["$defs"]["CompatibilityCriterionReference"]["properties"][
        "question_quote"
    ]["description"]
    assert "naming a type that already lives in the household does not establish one" in compatibility_description
    if case_id in {"Q02", "Q16"}:
        expected_limit = 2 if case_id == "Q02" else 1
        assert parsed.recommendation_limit == expected_limit
    if case_id == "Q16":
        assert schema["properties"]["requested_compatibility"]["description"]
    if case_id in {"Q09", "Q10"}:
        assert parsed.household_facts == []
    if case_id == "Q11":
        assert len(parsed.household_facts) == 1
        assert all(
            fact.fact_type is None
            and fact.value is None
            and fact.existing_stone_type is None
            for fact in parsed.household_facts
        )
    state: Any = {
        "question": question,
        "tools_used": 0,
        "question_fragments": fragments,
        "parsed_question": parsed,
        **grounded,
    }
    planned: Any = await workflow.plan_tools(state, runtime=Runtime(context=context))
    assert "search_candidates" in planned["permitted_tools"], case_id
    assert "search_candidates" not in planned["blocked_tools"], case_id
    if case_id == "Q02":
        assert parsed.requested_availability == []
        assert planned["permitted_tools"] == ["search_candidates"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "parsed_quote", "omitted_quote"),
    [
        (
            "Find one stone who stays quiet in the early morning.",
            "stays quiet",
            "in the early morning",
        ),
        (
            "Find one stone, but only if it comes from the northern shelter.",
            "Find one stone",
            "only if it comes from the northern shelter",
        ),
    ],
    ids=["missing-operative-qualifier", "unrepresented-hard-constraint"],
)
async def test_schema_audit_blocks_missing_or_unrepresented_constraints(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    parsed_quote: str,
    omitted_quote: str,
) -> None:
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requirements": {
                "character": [{"fragment_id": 1, "question_quote": parsed_quote}]
            },
            "retrieval": {
                "lexical_query": "quiet stone",
                "semantic_query": "stone suited to the request",
            },
        }
    )

    class Model:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def respond(messages: Any) -> dict[str, Any]:
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": GroundingResponse(
                        decisions=[],
                        question_coverage=QuestionCoverageAudit(
                            status="incomplete",
                            summary="An independent decision constraint is missing from the parse.",
                            issues=[
                                QuestionCoverageIssue(
                                    kind="omitted",
                                    fragment_id=1,
                                    quote=omitted_quote,
                                    reason="This source-bound constraint is not represented by a parsed criterion.",
                                )
                            ],
                        ),
                    ),
                }

            return RunnableLambda(respond)

    monkeypatch.setattr(workflow, "get_config", lambda: {})
    context: Any = SimpleNamespace(
        grounding_catalog=AsyncMock(load=AsyncMock(return_value=snapshot())),
        evaluation_model=Model(),
        evaluation_uses_json_schema=True,
        evaluation_reasoning=None,
    )
    fragments = {1: question}
    grounded: Any = await workflow.ground_question(
        {
            "question": question,
            "question_fragments": fragments,
            "parsed_question": parsed,
            "messages": [],
            "tools_used": 0,
        },
        runtime=Runtime(context=context),
    )
    assert grounded["question_coverage_status"] == "incomplete"
    issue = grounded["question_coverage_audit"]["issues"][0]
    assert issue["quote"] == omitted_quote
    state: Any = {
        "question": question,
        "question_fragments": fragments,
        "parsed_question": parsed,
        "criteria": grounded["criteria"],
        "reference_request": grounded["reference_request"],
        "messages": [],
        "tools_used": 0,
        **grounded,
    }
    planned: Any = await workflow.plan_tools(state, runtime=Runtime(context=context))
    assert planned["plan_status"] == "question_coverage_incomplete"
    assert planned["blocked_tools"] == ["search_candidates"]
    assert "search_candidates" not in planned["permitted_tools"]


def snapshot() -> Any:
    return build_grounding_snapshot(
        [
            GroundingEntry.model_validate(e)
            for e in json.loads(
                (ROOT / "fixtures/knowledge/grounding/grounding_en-v1.json").read_text()
            )
        ],
        "en",
        "en-v1",
    )


def test_all_held_out_inputs_use_current_source_bound_atoms() -> None:
    for case in HOLDOUT:
        parsed = parsed_grounding_case(case)
        fragments = {1: case["question"]}
        atoms = parsed.parsed_atoms(fragments)
        validate_parsed_atoms(atoms, fragments)
        proposals = parsed.grounding_proposals(fragments)
        assert len(proposals) == 1
        assert proposals[0].question_quote in case["question"]


def proposal_for(case: dict[str, Any]) -> ParseQuestion:
    return parsed_grounding_case(case)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", HOLDOUT, ids=lambda c: c["id"])
async def test_only_bound_supported_decisions_become_facts_or_filters(case: dict[str, Any]) -> None:
    parsed = proposal_for(case)
    proposals = parsed.grounding_proposals({1: case["question"]})
    seen = []

    class Model:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            assert schema is GroundingResponse

            def respond(messages: Any) -> dict[str, Any]:
                seen.append(json.loads(messages[-1].content))
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": GroundingResponse(
                        decisions=[
                            GroundingDecision(
                                proposal_id=proposals[0].proposal_id,
                                finding=case["expected"],
                                fragment_id=1,
                                quote=case["question"],
                                reason="Fixture decision for contract verification.",
                            )
                        ],
                        question_coverage=QuestionCoverageAudit(
                            status="complete", summary="Every parsed atom is covered."
                        ),
                    ),
                }

            return RunnableLambda(respond)

    ctx: Any = SimpleNamespace(
        grounding_catalog=AsyncMock(load=AsyncMock(return_value=snapshot())),
        evaluation_model=Model(),
        evaluation_uses_json_schema=True,
        evaluation_reasoning=None,
    )

    async def run(state: Any) -> dict[str, object]:
        return await workflow.ground_question(state, runtime=Runtime(context=ctx))

    result: Any = await RunnableLambda(run).ainvoke(
        {
            "question": case["question"],
            "question_fragments": {1: case["question"]},
            "parsed_question": parsed,
        }
    )
    assert seen[0]["original_question"] == case["question"]
    assert seen[0]["catalog"]["content_hash"] == snapshot().content_hash
    assert result["grounding_status"] == "verified"
    assert result["question_coverage_status"] == "complete"
    if case["concept_id"] == "candidate_type" and case["expected"] != "supported":
        assert result["criteria_status"] == "unverified_candidate_type" and "criteria" not in result
    else:
        assert result["criteria_status"] == "parsed"
        if case["concept_id"] == "candidate_type":
            assert result["retrieval"].filters.stone_type.value == case["proposed_type"]
        else:
            facts = result["criteria"].household_facts
            assert bool(facts) == (case["expected"] == "supported")
            if facts:
                assert facts[0].value is case["proposed_value"]


@pytest.mark.asyncio
async def test_unavailable_catalog_is_not_semantic_unknown_or_silent_filter_removal() -> None:
    case = HOLDOUT[0]
    ctx: Any = SimpleNamespace(
        grounding_catalog=AsyncMock(load=AsyncMock(side_effect=TimeoutError())),
        evaluation_model=AsyncMock(),
    )
    result = await workflow.ground_question(
        {
            "question": case["question"],
            "question_fragments": {1: case["question"]},
            "parsed_question": proposal_for(case),
            "messages": [],
            "tools_used": 0,
        },
        runtime=Runtime(context=ctx),
    )
    assert result["grounding_status"] == "grounding_unavailable"
    assert "criteria" not in result
    ctx.evaluation_model.with_structured_output.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("coverage_status", ["incomplete", "uncertain"])
async def test_zero_proposal_recommendation_runs_coverage_audit_and_blocks_search(
    monkeypatch: pytest.MonkeyPatch,
    coverage_status: Literal["incomplete", "uncertain"],
) -> None:
    question = "Tell me about Svetlana and find one companion who is calm and likes children."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
            "retrieval": {"lexical_query": "companion", "semantic_query": "calm companion"},
        }
    )
    model_calls = 0

    class Model:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def respond(messages: Any) -> dict[str, Any]:
                nonlocal model_calls
                model_calls += 1
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": GroundingResponse(
                        decisions=[],
                        question_coverage=QuestionCoverageAudit(
                            status=coverage_status,
                            summary="One independent criterion was not captured.",
                            issues=[
                                QuestionCoverageIssue(
                                    kind="omitted",
                                    fragment_id=1,
                                    quote="likes children",
                                    reason="This preference has no parsed atom.",
                                )
                                if coverage_status == "incomplete"
                                else QuestionCoverageIssue(
                                    kind="uncertain",
                                    reason="The request needs clarification before it can be checked.",
                                )
                            ],
                        ),
                    ),
                }

            return RunnableLambda(respond)

    context: Any = SimpleNamespace(
        grounding_catalog=AsyncMock(load=AsyncMock(return_value=snapshot())),
        evaluation_model=Model(),
        evaluation_uses_json_schema=True,
        evaluation_reasoning=None,
    )
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    grounded = await workflow.ground_question(
        {
            "question": question,
            "messages": [],
            "tools_used": 0,
            "question_fragments": {1: question},
            "parsed_question": parsed,
        },
        runtime=Runtime(context=context),
    )
    assert model_calls == 1
    assert grounded["question_coverage_status"] == coverage_status
    state: Any = {
        "question": question,
        "tools_used": 0,
        "messages": [],
        "question_fragments": {1: question},
        "parsed_question": parsed,
        **grounded,
    }
    planned = await workflow.plan_tools(state, runtime=Runtime(context=context))
    assert planned["plan_status"] == "accepted"
    assert planned["blocked_tools"] == ["search_candidates"]
    permitted = planned["permitted_tools"]
    assert isinstance(permitted, list)
    assert "search_candidates" not in permitted
    assert "get_stone_details" in permitted
    planned_state = cast(workflow.SearchState, {**state, **planned})
    assert workflow.after_planning(planned_state) == "execute_reference_plan"
    planned_state["reference_result"] = ReferenceResult(
        lines=["Svetlana's profile says she enjoys loud morning singing."]
    )
    answer = await workflow.answer_reference(
        planned_state, runtime=Runtime(context=context)
    )
    answer_result = cast(dict[str, object], answer["result"])
    answer_text = cast(str, answer_result["answer"])
    assert "Svetlana's profile says she enjoys loud morning singing." in answer_text
    assert "No recommendation was made" in answer_text
    assert workflow.after_reference_answer(
        cast(workflow.SearchState, {**planned_state, **answer})
    ) == "done"


@pytest.mark.parametrize(
    "failure", ["duplicate", "missing", "unknown_id", "wrong_quote", "wrong_fragment"]
)
def test_grounding_rejects_incomplete_or_unbound_decisions(failure: str) -> None:
    case = HOLDOUT[0]
    proposals = proposal_for(case).grounding_proposals({1: case["question"]})
    decision = GroundingDecision(
        proposal_id=proposals[0].proposal_id,
        finding="supported",
        fragment_id=1,
        quote=case["question"],
        reason="Fixture",
    )
    decisions = [decision]
    if failure == "duplicate":
        decisions.append(decision)
    elif failure == "missing":
        decisions = []
    elif failure == "unknown_id":
        decision.proposal_id = "invented"
    elif failure == "wrong_quote":
        decision.quote = "Fabricated agreement."
    elif failure == "wrong_fragment":
        decision.fragment_id = 2
    with pytest.raises(ValueError):
        validate_grounding_response(
            GroundingResponse(
                decisions=decisions,
                question_coverage=QuestionCoverageAudit(
                    status="complete", summary="No coverage issue in this binding test."
                ),
            ),
            proposals,
            {1: case["question"]},
        )


def test_two_agreements_in_one_fragment_keep_independent_source_bound_ids() -> None:
    question = "We agreed to rotate decisions, and we agreed on a deadline."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "agreed to rotate decisions",
                    "fact_type": "decision_rotation_agreed",
                    "value": True,
                },
                {
                    "fragment_id": 1,
                    "question_quote": "agreed on a deadline",
                    "fact_type": "decision_deadline_agreed",
                    "value": True,
                },
            ],
        }
    )
    proposals = parsed.grounding_proposals({1: question})
    assert [proposal.question_quote for proposal in proposals] == [
        "agreed to rotate decisions",
        "agreed on a deadline",
    ]
    decisions = [
        GroundingDecision(
            proposal_id=proposal.proposal_id,
            finding="supported",
            fragment_id=proposal.fragment_id,
            quote=proposal.question_quote,
            reason="The exact agreement is stated in the cited subquote.",
        )
        for proposal in proposals
    ]
    with pytest.raises(ValueError, match="proposal's original fragment"):
        decisions[0].quote = proposals[1].question_quote
        validate_grounding_response(
            GroundingResponse(
                decisions=decisions,
                question_coverage=QuestionCoverageAudit(
                    status="complete", summary="Both agreements are parsed."
                ),
            ),
            proposals,
            {1: question},
        )

    decisions[0].quote = proposals[0].question_quote
    assert validate_grounding_response(
        GroundingResponse(
            decisions=decisions,
            question_coverage=QuestionCoverageAudit(
                status="complete", summary="Both agreements are parsed."
            ),
        ),
        proposals,
        {1: question},
    ) == frozenset({"agreement:0", "agreement:1"})
    criteria, _ = parsed.resolve({1: question}, frozenset({"agreement:0", "agreement:1"}))
    assert len(criteria.household_facts) == 2
    assert len({fact.criterion_id for fact in criteria.household_facts}) == 2


def test_same_fragment_requirement_and_preference_remain_distinct_atoms() -> None:
    question = "Must stay quiet in the morning, and ideally enjoy company."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requirements": {
                "character": [
                    {"fragment_id": 1, "question_quote": "Must stay quiet in the morning"}
                ]
            },
            "preferences": {
                "character": [
                    {"fragment_id": 1, "question_quote": "ideally enjoy company"}
                ]
            },
        }
    )
    atoms = parsed.parsed_atoms({1: question})
    validate_parsed_atoms(atoms, {1: question})
    criteria, duplicates = parsed.resolve({1: question})
    assert duplicates == 0
    assert len(criteria.requirements.character) == 1
    assert len(criteria.preferences.character) == 1
    assert criteria.requirements.character[0].criterion_id != criteria.preferences.character[0].criterion_id
    assert {str(atom["category"]) for atom in atoms} == {"requirement_character", "preference_character"}


def test_coverage_audit_requires_bound_explicit_issues() -> None:
    question = "Find a companion who is calm and likes children."
    atoms = [
        {
            "atom_id": "requirement.character.1",
            "category": "requirement_character",
            "fragment_id": 1,
            "quote": "calm",
        }
    ]
    validate_question_coverage(
        QuestionCoverageAudit(
            status="incomplete",
            summary="A criterion was omitted.",
            issues=[
                QuestionCoverageIssue(
                    kind="omitted",
                    fragment_id=1,
                    quote="likes children",
                    reason="This independent requirement is absent from the parsed atoms.",
                )
            ],
        ),
        atoms,
        {1: question},
    )
    bad_issues = [
        QuestionCoverageIssue(
            kind="misclassified",
            atom_id="requirement.character.1",
            fragment_id=1,
            quote="likes children",
            reason="The parsed role is wrong.",
        )
    ]
    with pytest.raises(ValueError, match="source-bound atom"):
        validate_question_coverage(
            QuestionCoverageAudit(
                status="incomplete", summary="Role mismatch.", issues=bad_issues
            ),
            atoms,
            {1: question},
        )


def test_coverage_audit_detects_household_type_misclassified_as_a_mandate() -> None:
    question = "Our granite lives here. Find a companion."
    atoms = [
        {
            "atom_id": "requirement.compatibility.1",
            "category": "requirement_compatibility",
            "fragment_id": 1,
            "quote": "Our granite lives here",
        }
    ]
    issue = QuestionCoverageIssue(
        kind="misclassified",
        atom_id="requirement.compatibility.1",
        fragment_id=1,
        quote="Our granite lives here",
        reason="Household presence does not state a compatibility requirement.",
    )
    validate_question_coverage(
        QuestionCoverageAudit(
            status="incomplete",
            summary="The household fact was misclassified as a constraint.",
            issues=[issue],
        ),
        atoms,
        {1: question},
    )
    with pytest.raises(ValueError, match="Complete question coverage"):
        validate_question_coverage(
            QuestionCoverageAudit(
                status="complete",
                summary="Contradiction in response.",
                issues=[issue],
            ),
            atoms,
            {1: question},
        )


def test_model_cannot_supply_operational_filters() -> None:
    with pytest.raises(ValidationError):
        RetrievalProposal.model_validate(
            {
                "lexical_query": "quiet",
                "semantic_query": "quiet home",
                "filters": {"language": "English"},
            }
        )


def test_holdout_does_not_reuse_catalog_example_wording() -> None:
    examples = {e.text for e in snapshot().entries if e.entry_kind == "example"}
    assert not examples.intersection(case["question"] for case in HOLDOUT)


def test_metrics_do_not_count_technical_failures_as_correct_rejections() -> None:
    metrics = grounding_metrics(
        ["supported", "unknown", "contradicted"], ["supported", None, "supported"]
    )
    assert metrics["technical_failures"] == 1
    assert metrics["false_acceptances"] == 1
    assert metrics["classification_accuracy"] == pytest.approx(1 / 3)
    assert metrics["acceptance_accuracy"] == pytest.approx(1 / 3)
    assert metrics["supported_precision"] == 0.5
