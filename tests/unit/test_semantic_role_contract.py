import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.question_grounding import (
    GroundingDecision,
    GroundingResponse,
    MisclassifiedCoverageIssue,
    QuestionCoverageAudit,
)
from stone_shelter_assistant.assistant.selection import (
    ParseQuestion,
    question_fragments,
)
from stone_shelter_assistant.search.knowledge.grounding_concept_store_service import (
    GroundingEntry,
    GroundingSnapshot,
    build_grounding_snapshot,
)
from stone_shelter_assistant.stones.enums import StoneType

ROOT = Path(__file__).parents[2]


def catalog_snapshot() -> GroundingSnapshot:
    entries = [
        GroundingEntry.model_validate(entry)
        for entry in json.loads(
            (ROOT / "fixtures/knowledge/grounding/grounding_en-v1.json").read_text()
        )
    ]
    return build_grounding_snapshot(entries, "en", "en-v1")


def valid_parse(question: str) -> ParseQuestion:
    return ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "marble already lives",
                    "existing_stone_type": "MARBLE",
                },
                {
                    "fragment_id": 2,
                    "question_quote": "We agreed to rotate decisions",
                    "fact_type": "decision_rotation_agreed",
                    "value": True,
                    "applies_to_pair": ["MARBLE", "SLATE"],
                },
                {
                    "fragment_id": 2,
                    "question_quote": "set a deadline for marble-slate pair only",
                    "fact_type": "decision_deadline_agreed",
                    "value": True,
                    "applies_to_pair": ["MARBLE", "SLATE"],
                },
            ],
            "requirements": {
                "character": [
                    {"fragment_id": 1, "question_quote": "for a quiet home"}
                ],
                "compatibility": [
                    {
                        "fragment_id": 4,
                        "target_type": "MARBLE",
                        "question_quote": "must live well with the marble already living there",
                    }
                ],
            },
            "retrieval": {
                "lexical_query": "slate quiet home marble",
                "semantic_query": "Find a slate stone suited to a quiet home and explicitly compatible with marble.",
                "candidate_type": {"fragment_id": 1, "stone_type": "SLATE"},
            },
        }
    )


class ParserFixture:
    def __init__(self, parsed: ParseQuestion) -> None:
        self.parsed = parsed
        self.messages: list[Any] = []

    def with_structured_output(self, schema: Any, **_: Any) -> Any:
        assert schema is ParseQuestion

        async def respond(messages: Any) -> dict[str, Any]:
            self.messages.extend(messages)
            return {
                "raw": AIMessage(content="{}", response_metadata={"finish_reason": "stop"}),
                "parsed": self.parsed,
            }

        return RunnableLambda(respond)


class GroundingFixture:
    def __init__(self, response: GroundingResponse) -> None:
        self.response = response
        self.payload: dict[str, Any] | None = None

    def with_structured_output(self, schema: Any, **_: Any) -> Any:
        assert schema["title"] == "GroundingResponse"

        def respond(messages: Any) -> dict[str, Any]:
            self.payload = json.loads(messages[-1].content)
            return {
                "raw": AIMessage(content="{}", response_metadata={"finish_reason": "stop"}),
                "parsed": self.response,
            }

        return RunnableLambda(respond)


def supported_response(proposals: list[Any]) -> GroundingResponse:
    return GroundingResponse(
        decisions=[
            GroundingDecision(
                proposal_id=proposal.proposal_id,
                finding="supported",
                fragment_id=proposal.fragment_id,
                quote=proposal.question_quote,
                reason="The authored concept and exact question span support this scoped fact.",
            )
            for proposal in proposals
        ],
        question_coverage=QuestionCoverageAudit(
            status="complete", summary="The typed parse covers each independent request and scope."
        ),
    )


@pytest.mark.asyncio
async def test_parser_and_auditor_share_one_authored_catalog_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    question = (
        "Find one slate stone for a quiet home where marble already lives. "
        "We agreed to rotate decisions and set a deadline for marble-slate pair only. "
        "The agreements do not apply to pumice pairs. It must live well with the marble already living there."
    )
    snapshot = catalog_snapshot()
    parsed = valid_parse(question)
    parser = ParserFixture(parsed)
    evaluator = GroundingFixture(supported_response(parsed.grounding_proposals(question_fragments(question))))
    catalog = SimpleNamespace(load=AsyncMock(return_value=snapshot))
    context = SimpleNamespace(
        grounding_catalog=catalog,
        models=SimpleNamespace(
            parsing_model=parser,
            evaluation_model=evaluator,
            evaluation_uses_json_schema=True,
            evaluation_reasoning=None,
        ),
    )

    parsed_state: Any = await workflow.parse_question(
        {"question": question, "messages": [], "tools_used": 0},
        runtime=Runtime(context=cast(Any, context)),
    )
    human_payload = json.loads(parser.messages[-1].content)
    assert human_payload["semantic_concepts"]["content_hash"] == snapshot.content_hash
    assert {entry["id"] for entry in human_payload["semantic_concepts"]["entries"]} == {
        entry.id for entry in snapshot.entries
    }
    assert parsed_state["grounding_catalog"]["content_hash"] == snapshot.content_hash
    assert parsed_state["grounding_catalog_snapshot"]["content_hash"] == snapshot.content_hash

    parse_output_state: Any = {
        "question": question,
        "messages": [],
        "tools_used": 0,
        **parsed_state,
    }
    grounded: Any = await workflow.ground_question(
        parse_output_state, runtime=Runtime(context=cast(Any, context))
    )
    assert catalog.load.await_count == 1
    assert evaluator.payload is not None
    assert evaluator.payload["catalog"]["content_hash"] == snapshot.content_hash
    assert grounded["grounding_catalog"]["content_hash"] == snapshot.content_hash
    assert grounded["question_coverage_status"] == "complete"
    criteria: Any = grounded["criteria"]
    assert criteria.requirements.character[0].question_quote == "for a quiet home"
    assert criteria.requirements.compatibility[0].household_type == StoneType.MARBLE
    assert criteria.compatibility_targets()[StoneType.MARBLE].required is True
    assert criteria.compatibility_targets()[StoneType.MARBLE].existing_household is True
    assert grounded["retrieval"].filters.stone_type == StoneType.SLATE
    scoped_facts = [fact for fact in criteria.household_facts if fact.fact_type is not None]
    assert [fact.applies_to_pair for fact in scoped_facts] == [
        (StoneType.MARBLE, StoneType.SLATE),
        (StoneType.MARBLE, StoneType.SLATE),
    ]
    assert all(fact.value is True for fact in scoped_facts)


@pytest.mark.asyncio
async def test_catalog_load_failure_does_not_retry_during_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    question = "Find a slate stone for a quiet home."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requirements": {
                "character": [{"fragment_id": 1, "question_quote": "for a quiet home"}]
            },
            "retrieval": {
                "lexical_query": "slate quiet home",
                "semantic_query": "A slate stone suited to a quiet home.",
                "candidate_type": {"fragment_id": 1, "stone_type": "SLATE"},
            },
        }
    )
    catalog = SimpleNamespace(load=AsyncMock(side_effect=TimeoutError("catalog unavailable")))
    parser = ParserFixture(parsed)
    evaluator = AsyncMock()
    context = SimpleNamespace(
        grounding_catalog=catalog,
        models=SimpleNamespace(
            parsing_model=parser,
            evaluation_model=evaluator,
            evaluation_uses_json_schema=True,
            evaluation_reasoning=None,
        ),
    )
    parsed_state: Any = await workflow.parse_question(
        {"question": question, "messages": [], "tools_used": 0},
        runtime=Runtime(context=cast(Any, context)),
    )
    parse_output_state: Any = {
        "question": question,
        "messages": [],
        "tools_used": 0,
        **parsed_state,
    }
    result: Any = await workflow.ground_question(
        parse_output_state, runtime=Runtime(context=cast(Any, context))
    )
    assert catalog.load.await_count == 1
    assert result["grounding_status"] == "grounding_unavailable"
    assert result["grounding_error_type"] == "TimeoutError"
    assert "criteria" not in result
    evaluator.with_structured_output.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "finding"),
    [
        ("Ideally find a granite stone.", "unknown"),
        ("Find a stone but not granite.", "contradicted"),
    ],
)
async def test_optional_or_negated_candidate_type_never_becomes_filter(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    finding: Literal["supported", "contradicted", "unknown"],
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "retrieval": {
                "lexical_query": "granite",
                "semantic_query": "A granite candidate, if allowed by the original question.",
                "candidate_type": {"fragment_id": 1, "stone_type": "GRANITE"},
            },
        }
    )
    snapshot = catalog_snapshot()
    proposal = parsed.grounding_proposals({1: question})[0]
    evaluator = GroundingFixture(
        GroundingResponse(
            decisions=[
                GroundingDecision(
                    proposal_id=proposal.proposal_id,
                    finding=finding,
                    fragment_id=1,
                    quote=proposal.question_quote,
                    reason="The field describes required, nonoptional candidate material.",
                )
            ],
            question_coverage=QuestionCoverageAudit(
                status="complete", summary="The request is represented without an optional filter."
            ),
        )
    )
    context = SimpleNamespace(
        grounding_catalog=AsyncMock(),
        models=SimpleNamespace(
            evaluation_model=evaluator,
            evaluation_uses_json_schema=True,
            evaluation_reasoning=None,
        ),
    )
    grounded: Any = await workflow.ground_question(
        {
            "question": question,
            "messages": [],
            "tools_used": 0,
            "question_fragments": {1: question},
            "parsed_question": parsed,
            "grounding_catalog_snapshot": snapshot.model_dump(mode="json"),
        },
        runtime=Runtime(context=cast(Any, context)),
    )
    assert grounded["criteria_status"] == "unverified_candidate_type"
    assert "retrieval" not in grounded
    assert "criteria" not in grounded


def test_household_context_and_explicit_hard_compatibility_resolve_differently() -> None:
    context_only, _ = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "marble already lives",
                    "existing_stone_type": "MARBLE",
                }
            ],
            "retrieval": {
                "lexical_query": "slate home marble",
                "semantic_query": "A slate stone for a home with marble.",
                "candidate_type": {"fragment_id": 1, "stone_type": "SLATE"},
            },
        }
        ).resolve(
            {1: "Find a slate stone for a home where marble already lives."},
            frozenset({"candidate_type"}),
        )
    context_target = context_only.compatibility_targets()[StoneType.MARBLE]
    assert context_target.existing_household is True
    assert context_target.required is False

    required, _ = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "marble already living here",
                    "existing_stone_type": "MARBLE",
                }
            ],
            "requirements": {
                "compatibility": [
                    {
                        "fragment_id": 2,
                        "target_type": "MARBLE",
                        "question_quote": "live well with marble",
                    }
                ]
            },
            "retrieval": {
                "lexical_query": "slate home marble",
                "semantic_query": "A slate stone required to live well with marble.",
                "candidate_type": {"fragment_id": 1, "stone_type": "SLATE"},
            },
        }
    ).resolve(
        {1: "Find a slate stone with marble already living here", 2: "It must live well with marble."},
        frozenset({"candidate_type"}),
    )
    required_target = required.compatibility_targets()[StoneType.MARBLE]
    assert required_target.existing_household is True
    assert required_target.required is True

    same_type, _ = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requirements": {
                "compatibility": [
                    {
                        "fragment_id": 1,
                        "target_type": "SLATE",
                        "question_quote": "must live well with another slate stone",
                    }
                ]
            },
            "retrieval": {
                "lexical_query": "slate pair",
                "semantic_query": "A slate candidate for a slate pairing.",
                "candidate_type": {"fragment_id": 1, "stone_type": "SLATE"},
            },
        }
    ).resolve(
        {1: "Find a slate stone that must live well with another slate stone."},
        frozenset({"candidate_type"}),
    )
    assert same_type.compatibility_targets()[StoneType.SLATE].required is True


@pytest.mark.asyncio
async def test_invalid_candidate_type_role_is_blocked_without_parse_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    question = "Find one granite stone for a quiet home where marble already lives."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "marble already lives",
                    "existing_stone_type": "MARBLE",
                }
            ],
            "requirements": {
                "character": [{"fragment_id": 1, "question_quote": "for a quiet home"}],
                "compatibility": [
                    {
                        "fragment_id": 1,
                        "target_type": "GRANITE",
                        "question_quote": "one granite stone",
                    }
                ],
            },
            "retrieval": {
                "lexical_query": "granite quiet home marble",
                "semantic_query": "A granite candidate for a quiet home.",
            },
        }
    )
    snapshot = catalog_snapshot()
    evaluator = GroundingFixture(
        GroundingResponse(
            decisions=[],
            question_coverage=QuestionCoverageAudit(
                status="incomplete",
                summary="The type of the new candidate is in the wrong field.",
                issues=[
                    MisclassifiedCoverageIssue(
                        kind="misclassified",
                        atom_id="requirement.compatibility.1",
                        fragment_id=1,
                        quote="one granite stone",
                        reason="The material modifies the new candidate noun; it is not a pair target.",
                    )
                ],
            ),
        )
    )
    context = SimpleNamespace(
        grounding_catalog=AsyncMock(),
        models=SimpleNamespace(
            evaluation_model=evaluator,
            evaluation_uses_json_schema=True,
            evaluation_reasoning=None,
        ),
    )
    invalid_state: Any = {
        "question": question,
        "messages": [],
        "tools_used": 0,
        "question_fragments": {1: question},
        "parsed_question": parsed,
        "grounding_catalog_snapshot": snapshot.model_dump(mode="json"),
    }
    grounded: Any = await workflow.ground_question(
        invalid_state, runtime=Runtime(context=cast(Any, context))
    )
    assert grounded["question_coverage_status"] == "incomplete"
    assert grounded["criteria"].requirements.compatibility[0].household_type == StoneType.GRANITE
    assert grounded["retrieval"].filters.stone_type is None
    assert not grounded["parser_diagnostics"]
    planned_state: Any = {"question": question, "messages": [], "tools_used": 0, **grounded}
    planned: Any = await workflow.plan_tools(
        planned_state, runtime=Runtime(context=cast(Any, SimpleNamespace()))
    )
    assert planned["plan_status"] == "question_coverage_incomplete"
    assert "search_candidates" not in planned["permitted_tools"]

