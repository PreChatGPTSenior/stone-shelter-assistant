"""Semantic-verifier contracts with fixture decisions; not a model-quality claim."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.runtime import Runtime
from pydantic import ValidationError
from tests.integration.test_grounding_model_evaluation import grounding_metrics

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.question_grounding import (
    GroundingDecision,
    GroundingResponse,
    validate_grounding_response,
)
from stone_shelter_assistant.assistant.selection import ParseQuestion, RetrievalProposal
from stone_shelter_assistant.search.knowledge.grounding_catalog import (
    GroundingEntry,
    build_grounding_snapshot,
)

ROOT = Path(__file__).parents[2]
HOLDOUT = json.loads((ROOT / "tests/fixtures/agent-eval/grounding-en/holdout.json").read_text())


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


def proposal_for(case: dict[str, Any]) -> ParseQuestion:
    data: dict[str, Any] = {"recommendation_limit": 1}
    data["retrieval"] = {"lexical_query": "companion", "semantic_query": "a suitable companion"}
    if case["concept_id"] == "candidate_type":
        data["retrieval"]["candidate_type"] = {
            "fragment_id": 1,
            "stone_type": case["proposed_type"],
        }
    else:
        data["household_facts"] = [
            {"fragment_id": 1, "fact_type": case["concept_id"], "value": case["proposed_value"]}
        ]
    return ParseQuestion.model_validate(data)


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
                        ]
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
            GroundingResponse(decisions=decisions), proposals, {1: case["question"]}
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
