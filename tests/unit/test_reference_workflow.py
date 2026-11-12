"""Exercise named information, unsupported care and scoped evidence through the graph."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_evaluation import CandidateEvidence
from stone_shelter_assistant.assistant.reference_evidence import (
    ReferenceAnswer,
    ReferenceEvidence,
    ReferenceScope,
    ReferenceSection,
    ReferenceSource,
    check_reference_quotes,
    reference_citations_valid,
)
from stone_shelter_assistant.assistant.reference_lookup import ReferenceTools
from stone_shelter_assistant.assistant.selection import ParseQuestion
from stone_shelter_assistant.assistant.tool_planning import ToolPlan, permitted_tools, plan_error
from stone_shelter_assistant.search.document_models import CompatibilityPairSearchDocument
from stone_shelter_assistant.search.knowledge.encyclopedia_document_builder import (
    build_encyclopedia_documents,
)
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
    build_stone_compatibility_documents,
)

ROOT = Path(__file__).parents[2]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "overview",
        "preferences",
        "care",
        "unsupported",
        "missing",
        "invalid_citation",
        "missing_scope",
        "history",
    ],
)
async def test_reference_graph_collects_scoped_sources_and_handles_missing_data(case: str) -> None:
    snapshot = json.loads(
        (ROOT / "tests/fixtures/assistant/quiet-home-assessment.json").read_text()
    )
    card: dict[str, Any] = next(c for c in snapshot["cards"] if c["name"] == "Madame Obsidian")
    if case in ("overview", "invalid_citation", "missing_scope", "history"):
        fixture = json.loads(
            (ROOT / "fixtures/stones/b19266ec-28a2-4fd3-851b-7fad50b6e175.json").read_text()
        )
        card = {
            **card,
            "name": "Svetlana",
            "stone_type": "MARBLE",
            "biography": fixture["stone"]["biography"],
            "profile": None,
            "shelter_case": {
                **card["shelter_case"],
                "external_id": fixture["shelterCase"]["externalId"],
            },
        }
    topic = (
        "overview"
        if case in ("overview", "missing", "invalid_citation", "missing_scope")
        else "history"
        if case == "history"
        else "preferences"
    )
    question = {
        "overview": "Tell me about Svetlana.",
        "invalid_citation": "Tell me about Svetlana.",
        "missing_scope": "Tell me about Svetlana.",
        "preferences": "What does Madame Obsidian like?",
        "care": "How should I care for obsidian?",
        "unsupported": "How should I care for onyx?",
        "missing": "Tell me about Missing Stone.",
        "history": "What is in Svetlana's history?",
    }[case]
    fields: dict[str, Any] = {"recommendation_limit": 0}
    if case == "care":
        fields["requested_care"] = [{"fragment_id": 1, "stone_type": "OBSIDIAN"}]
    elif case == "unsupported":
        fields["unsupported_care"] = [{"fragment_id": 1, "material": "onyx"}]
    else:
        fields.update(
            named_stone={
                "fragment_id": 1,
                "name": "Missing Stone" if case == "missing" else card["name"],
            },
            requested_stone_info={"fragment_id": 1, "topic": topic},
        )
    parsed = ParseQuestion.model_validate(fields)
    criteria, _ = parsed.resolve({1: question})
    request = parsed.resolve_references({1: question})
    allowed = permitted_tools(criteria, request)
    path = "fixtures/knowledge/stone-encyclopedias/stone-encyclopedia_en.md"
    chapters = build_encyclopedia_documents((ROOT / path).read_text(), path)
    path = "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"
    guide = build_stone_compatibility_documents((ROOT / path).read_text(), path)
    calls: list[str] = []
    model_calls: list[type[Any]] = []

    @tool
    async def get_stone_status_by_name(name: str) -> list[dict[str, Any]]:
        """Read the fixture identity and current status."""
        calls.append("identity")
        return (
            []
            if case == "missing"
            else [
                {
                    "stone_id": card["id"],
                    "name": card["name"],
                    "stone_type": card["stone_type"],
                    "adoption_status": "AVAILABLE",
                }
            ]
        )

    @tool
    async def get_stone_details(stone_id: str) -> dict[str, Any]:
        """Read the individual fixture card."""
        calls.append("card")
        assert stone_id == card["id"]
        return card

    @tool
    async def get_case_timeline(case_external_id: str) -> list[dict[str, str]]:
        """Read the fixture case's authoritative chronological history."""
        assert case_external_id == card["shelter_case"]["external_id"]
        return [
            {
                "event_external_id": event["externalId"],
                "event_type": event["eventType"],
                "occurred_at": event["occurredAt"],
                "event_notes": event["eventNotes"],
            }
            for event in json.loads(
                (ROOT / "fixtures/stones/b19266ec-28a2-4fd3-851b-7fad50b6e175.json").read_text()
            )["shelterCase"]["events"]
        ]

    @tool
    async def search_knowledge_lexical(filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        """Read actual authored reference chapters and portraits."""
        calls.append(filters["document_kind"])
        assert filters["stone_type"] == card["stone_type"] or case == "care"
        return [
            d.model_dump(mode="json")
            for d in [*chapters, *guide]
            if d.model_dump()["document_kind"] == filters["document_kind"]
            and filters["stone_type"] in d.stone_types
        ][:limit]

    @tool
    async def list_compatibility_pairs(stone_type: str, verdict: str) -> list[dict[str, Any]]:
        """Read all authored partners for one type and verdict."""
        calls.append("pairs")
        return [
            d.model_dump(mode="json")
            for d in guide
            if isinstance(d, CompatibilityPairSearchDocument)
            and stone_type in d.stone_types
            and d.verdict == verdict
        ]

    class FixtureModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def respond(messages: Any) -> dict[str, Any]:
                model_calls.append(schema)
                if schema is ParseQuestion:
                    output: Any = parsed
                elif schema is ToolPlan:
                    output = ToolPlan(tools=allowed, reason="Cover the parsed reference request")
                elif schema is ReferenceEvidence:
                    data = json.loads(messages[-1].content)
                    output = ReferenceEvidence.model_validate(
                        {
                            "quotes": [
                                {"source_id": s["source_id"], "quote": s["text"]}
                                for s in data["sources"]
                                if case != "missing_scope" or s["scope"] != "history"
                            ]
                        }
                    )
                elif schema is ReferenceAnswer:
                    data = json.loads(messages[-1].content)
                    grouped: dict[ReferenceScope, list[dict[str, Any]]] = {
                        q["scope"]: [] for q in data["quotes"]
                    }
                    for quote in data["quotes"]:
                        grouped[quote["scope"]].append(quote)
                    output = ReferenceAnswer(
                        sections=[
                            ReferenceSection(
                                scope=scope,
                                explanation="\n".join(q["quote"] for q in group),
                                source_ids=[q["source_id"] for q in group],
                            )
                            for scope, group in grouped.items()
                        ]
                    )
                    if case == "invalid_citation":
                        output.sections[0].source_ids = ["invented-source"]
                else:
                    raise AssertionError(schema)
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": output,
                }

            return RunnableLambda(respond)

    model: Any = FixtureModel()
    result: Any = await workflow.run_workflow(
        question,
        grounding_catalog=AsyncMock(),
        selection_model=model,
        selection_uses_json_schema=True,
        parsing_model=model,
        planning_model=model,
        evaluation_model=model,
        evaluation_uses_json_schema=True,
        answer_model=model,
        retrieval_tools=[],
        details_tool=get_stone_details,
        status_tool=get_stone_status_by_name,
        timeline_tool=get_case_timeline,
        compatibility_tool=list_compatibility_pairs,
        encyclopedia_tool=search_knowledge_lexical,
        reference_tools=ReferenceTools(
            stone_status=get_stone_status_by_name,
            stone_details=get_stone_details,
            timeline=get_case_timeline,
            encyclopedia=search_knowledge_lexical,
            exact_pair=list_compatibility_pairs,
            pair_list=list_compatibility_pairs,
        ),
    )
    assert result["recommended_stone_ids"] == []
    if case == "unsupported":
        assert "No authored encyclopedia care information is available for onyx" in result["answer"]
        assert (
            calls == []
            and ReferenceEvidence not in model_calls
            and ReferenceAnswer not in model_calls
        )
    elif case == "missing":
        assert "No stone found" in result["answer"]
        assert calls == ["identity"] and not result["sources"]
    else:
        assert ReferenceEvidence in model_calls and ReferenceAnswer in model_calls
        if case == "care":
            assert calls == ["encyclopedia_section"]
        else:
            assert calls[:2] == ["identity", "card"]
            assert result["verified_statuses"][card["id"]] == "AVAILABLE"
        if case in ("overview", "invalid_citation", "missing_scope"):
            assert "compatibility_type_portrait" in calls and calls.count("pairs") == 3
            assert len(result["sources"]) == 18
            assert "singing loudly" in result["answer"]
            assert "General type information" in result["answer"]
            assert "General type compatibility" in result["answer"]
            if case == "missing_scope":
                assert "No validated summary for this scope" in result["answer"]
        elif case == "preferences":
            assert calls == ["identity", "card"]
            assert "peaceful home" in result["answer"]
        elif case == "history":
            assert "case-event:" in result["answer"]
            assert "05:00" in result["answer"]
        assert "invented-source" not in result["answer"]


def test_reference_evidence_rejects_invented_quotes_and_cross_scope_citations() -> None:
    sources = {
        "one": ReferenceSource(source_id="one", scope="encyclopedia", text="General type traits.")
    }
    evidence = ReferenceEvidence.model_validate(
        {
            "quotes": [
                {"source_id": "one", "quote": "General type traits."},
                {"source_id": "one", "quote": "Invented individual preference."},
                {"source_id": "missing", "quote": "General type traits."},
            ]
        }
    )
    accepted, rejected = check_reference_quotes(evidence, sources)
    assert len(accepted) == 1 and accepted[0].scope == "encyclopedia"
    assert {r["reason"] for r in rejected} == {"non_verbatim_quote", "unknown_source_ref"}
    answer = ReferenceAnswer(
        sections=[
            ReferenceSection(
                scope="individual", explanation="Individual preference", source_ids=["one"]
            )
        ]
    )
    assert not reference_citations_valid(answer, accepted)


def test_named_overview_requires_identity_and_card_before_type_knowledge() -> None:
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 0,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
        }
    )
    criteria, _ = parsed.resolve({1: "Tell me about Svetlana."})
    request = parsed.resolve_references({1: "Tell me about Svetlana."})
    allowed = permitted_tools(criteria, request)
    assert (
        plan_error(ToolPlan(tools=allowed, reason="Read identity before type"), allowed, request)
        is None
    )
    bad = [allowed[0], allowed[3], allowed[1], *allowed[2:3], *allowed[4:]]
    assert (
        plan_error(ToolPlan(tools=bad, reason="Wrong dependency order"), allowed, request)
        == "stone_card_must_be_read_before_type_knowledge"
    )
    mixed_criteria = criteria.model_copy(update={"recommendation_limit": 1})
    mixed_allowed = permitted_tools(mixed_criteria, request)
    assert (
        plan_error(
            ToolPlan(tools=mixed_allowed, reason="Incomplete mixed request"), mixed_allowed, request
        )
        == "named_information_not_covered"
    )


@pytest.mark.asyncio
async def test_eight_household_pairs_are_all_checked_and_rendered() -> None:
    snapshot = json.loads(
        (ROOT / "tests/fixtures/assistant/quiet-home-assessment.json").read_text()
    )
    card = next(c for c in snapshot["cards"] if c["name"] == "Sir Pebble")
    targets = [
        "OBSIDIAN",
        "BASALT",
        "MARBLE",
        "LIMESTONE",
        "SLATE",
        "SANDSTONE",
        "PUMICE",
        "GNEISS",
    ]
    question = "Find one granite stone for our home with " + ", ".join(targets) + "."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {"fragment_id": 1, "existing_stone_type": target} for target in targets
            ],
        }
    )
    criteria, _ = parsed.resolve({1: question})
    path = "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"
    guide = build_stone_compatibility_documents((ROOT / path).read_text(), path)
    pairs = {d.pair_key: d for d in guide if isinstance(d, CompatibilityPairSearchDocument)}
    looked_up = []

    @tool
    async def get_compatibility_pair(first_type: str, second_type: str) -> dict[str, Any]:
        """Load each authored household pair exactly once."""
        from stone_shelter_assistant.stones.enums import StoneType

        key = build_pair_key(StoneType(first_type), StoneType(second_type))
        looked_up.append(key)
        return pairs[key].model_dump(mode="json")

    @tool
    async def get_stone_details(stone_id: str) -> dict[str, Any]:
        """The fixture card has already been read."""
        raise AssertionError("Unexpected card lookup")

    @tool
    async def get_case_timeline(case_external_id: str) -> list[dict[str, str]]:
        """No observations are needed for this compatibility-only fixture."""
        return []

    class EmptyEvidenceModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            assert schema is CandidateEvidence
            return RunnableLambda(
                lambda _: {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": CandidateEvidence(character=[], individual_compatibility=[]),
                }
            )

    context: Any = SimpleNamespace(
        compatibility_tool=get_compatibility_pair,
        encyclopedia_tool=get_stone_details,
        timeline_tool=get_case_timeline,
        evaluation_model=EmptyEvidenceModel(),
        evaluation_uses_json_schema=True,
        evaluation_reasoning=None,
        details_tool=get_stone_details,
    )
    builder = StateGraph(workflow.SearchState, context_schema=workflow.RunContext)
    builder.add_node("evaluate_candidates", workflow.evaluate_candidates)
    builder.add_node("answer", workflow.answer)
    builder.add_edge(START, "evaluate_candidates")
    builder.add_edge("evaluate_candidates", "answer")
    builder.add_edge("answer", END)
    state = await builder.compile().ainvoke(
        {
            "question": question,
            "messages": [],
            "tools_used": 0,
            "criteria": criteria,
            "candidate_cards": {card["id"]: card},
            "verified_statuses": {card["id"]: "AVAILABLE"},
        },
        context=context,
    )
    expected = {"+".join(sorted(("GRANITE", t))) for t in targets}
    assert len(looked_up) == 8 and set(looked_up) == expected
    result: Any = state["result"]
    assert result["candidate_decisions"][0]["outcome"] == "conditional_option"
    assert result["recommended_stone_ids"] == []
    assert all(key in result["answer"] for key in expected)
    assert result["answer"].count("conditions: `unmarked`") == 3
