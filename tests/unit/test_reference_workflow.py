"""Exercise named information, unsupported care and scoped evidence through the graph."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

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
from stone_shelter_assistant.assistant.selection import ParseQuestion, SelectCandidates
from stone_shelter_assistant.assistant.tool_planning import ToolPlan, permitted_tools, plan_error
from stone_shelter_assistant.search.document_models import CompatibilityPairSearchDocument
from stone_shelter_assistant.search.knowledge.encyclopedia_document_builder import (
    build_encyclopedia_documents,
)
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
    build_stone_compatibility_documents,
)
from stone_shelter_assistant.stones.enums import StoneType

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
        "mixed",
    ],
)
async def test_reference_graph_collects_scoped_sources_and_handles_missing_data(case: str) -> None:
    snapshot = json.loads(
        (ROOT / "tests/fixtures/assistant/quiet-home-assessment.json").read_text()
    )
    card: dict[str, Any] = next(c for c in snapshot["cards"] if c["name"] == "Madame Obsidian")
    if case in ("overview", "invalid_citation", "missing_scope", "history", "mixed"):
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
        "mixed": "Tell me about Svetlana, find a quiet companion, and explain how to care for obsidian.",
    }[case]
    fields: dict[str, Any] = {"recommendation_limit": 1 if case == "mixed" else 0}
    if case == "mixed":
        fields["retrieval"] = {"lexical_query": "quiet", "semantic_query": "quiet companion"}
        fields["requested_care"] = [{"fragment_id": 1, "stone_type": "OBSIDIAN"}]
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
        assert limit == 1
        calls.append(filters["document_kind"])
        assert filters["stone_type"] == card["stone_type"] or case in {"care", "mixed"}
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

    @tool
    async def search_stones_hybrid(
        lexical_query: str, semantic_query: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Return no available candidate hits for this mixed-route test."""
        calls.append("candidate-search")
        return {"candidates": [], "dropped": []}

    search_stones_hybrid.metadata = {"retrieval_calls": 2}

    class FixtureModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def respond(messages: Any) -> dict[str, Any]:
                model_calls.append(schema)
                if schema is ParseQuestion:
                    output: Any = parsed
                elif schema is ToolPlan:
                    output = ToolPlan(tools=allowed, reason="Cover the parsed reference request")
                elif schema is SelectCandidates:
                    output = SelectCandidates(stone_ids=[])
                elif schema is ReferenceEvidence:
                    data = json.loads(messages[-1].content)
                    output = ReferenceEvidence.model_validate(
                        {
                            "quotes": [
                                {"source_id": s["source_id"], "quote": s["text"]}
                                for s in data["sources"]
                                if case != "missing_scope" or s["scope"] != "history"
                                if case != "mixed" or s["scope"] != "encyclopedia"
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
        retrieval_tools=[search_stones_hybrid] if case == "mixed" else [],
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
    if case == "mixed":
        assert calls[0:2] == ["identity", "card"]
        assert "candidate-search" in calls
        assert result["reference_answer_status"] == "generated"
        assert "singing loudly" in result["answer"]
        assert "General type information" in result["answer"]
        assert "abrasive particles" in result["answer"]
        assert result["question"] == question
        assert "encyclopedia:en:obsidian" in result["sources"]
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


@pytest.mark.asyncio
async def test_exact_compatibility_pairs_reach_reference_evidence_and_answer() -> None:
    path = "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"
    guide = build_stone_compatibility_documents((ROOT / path).read_text(), path)
    pairs = {
        document.pair_key: document
        for document in guide
        if isinstance(document, CompatibilityPairSearchDocument)
    }
    card: dict[str, Any] = next(
        c
        for c in json.loads(
            (ROOT / "tests/fixtures/assistant/quiet-home-assessment.json").read_text()
        )["cards"]
        if c["name"] == "Sir Pebble"
    )
    scenarios: dict[str, dict[str, Any]] = {
        "types": {
            "question": "Explain the GRANITE plus GRANITE compatibility rule and agreement.",
            "fields": {
                "recommendation_limit": 0,
                "requested_compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "GRANITE",
                        "first_type": "GRANITE",
                        "target": "types",
                    }
                ],
            },
            "pair_key": "GRANITE+GRANITE",
        },
        "named": {
            "question": "How does Sir Pebble pair with GRANITE, and what agreement is needed?",
            "fields": {
                "recommendation_limit": 0,
                "named_stone": {"fragment_id": 1, "name": "Sir Pebble"},
                "requested_compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "GRANITE",
                        "target": "named_stone",
                    }
                ],
            },
            "pair_key": "GRANITE+GRANITE",
        },
        "harmonious": {
            "question": "Explain the GRANITE plus OBSIDIAN compatibility rule.",
            "fields": {
                "recommendation_limit": 0,
                "requested_compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "OBSIDIAN",
                        "first_type": "GRANITE",
                        "target": "types",
                    }
                ],
            },
            "pair_key": "GRANITE+OBSIDIAN",
        },
        "no_evidence": {
            "question": "Explain the GRANITE plus GRANITE compatibility rule and agreement.",
            "fields": {
                "recommendation_limit": 0,
                "requested_compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "GRANITE",
                        "first_type": "GRANITE",
                        "target": "types",
                    }
                ],
            },
            "pair_key": "GRANITE+GRANITE",
        },
        "missing": {
            "question": "Explain the GRANITE plus GNEISS compatibility rule.",
            "fields": {
                "recommendation_limit": 0,
                "requested_compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "GNEISS",
                        "first_type": "GRANITE",
                        "target": "types",
                    }
                ],
            },
            "pair_key": None,
        },
        "mixed": {
            "question": (
                "Find a quiet companion, explain how to care for OBSIDIAN, and explain the "
                "GRANITE plus GRANITE compatibility rule."
            ),
            "fields": {
                "recommendation_limit": 1,
                "retrieval": {"lexical_query": "quiet", "semantic_query": "quiet companion"},
                "requested_care": [{"fragment_id": 1, "stone_type": "OBSIDIAN"}],
                "requested_compatibility": [
                    {
                        "fragment_id": 1,
                        "household_type": "GRANITE",
                        "first_type": "GRANITE",
                        "target": "types",
                    }
                ],
            },
            "pair_key": "GRANITE+GRANITE",
        },
    }

    scenarios["verdict_only"] = dict(scenarios["types"])
    scenarios["overview_partial"] = {
        "question": "Tell me about Sir Pebble and explain his compatibility with GRANITE.",
        "fields": {
            "recommendation_limit": 0,
            "named_stone": {"fragment_id": 1, "name": "Sir Pebble"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
            "requested_compatibility": [
                {"fragment_id": 1, "household_type": "GRANITE", "target": "named_stone"}
            ],
        },
        "pair_key": "GRANITE+GRANITE",
    }

    async def run_scenario(scenario_name: str, scenario: dict[str, Any]) -> None:
        question = scenario["question"]
        parsed = ParseQuestion.model_validate(scenario["fields"])
        criteria, _ = parsed.resolve({1: question})
        request = parsed.resolve_references({1: question})
        allowed = permitted_tools(criteria, request)
        evidence_inputs: list[dict[str, Any]] = []
        answer_inputs: list[dict[str, Any]] = []
        calls: list[str] = []
        current_scenario = scenario_name
        current_parse = parsed
        current_allowed_tools = allowed
        current_evidence_inputs = evidence_inputs
        current_answer_inputs = answer_inputs
        current_calls = calls

        @tool
        async def get_stone_status_by_name(name: str) -> list[dict[str, Any]]:
            """Read Sir Pebble's authoritative type and status."""
            current_calls.append("identity")
            assert name == "Sir Pebble"
            return [
                {
                    "stone_id": card["id"],
                    "name": card["name"],
                    "stone_type": card["stone_type"],
                    "adoption_status": "AVAILABLE",
                }
            ]

        @tool
        async def get_stone_details(stone_id: str) -> dict[str, Any]:
            """Read the card only for the combined named overview."""
            assert current_scenario == "overview_partial" and stone_id == card["id"]
            return card

        @tool
        async def get_case_timeline(case_external_id: str) -> list[dict[str, str]]:
            """Read an empty timeline only for the combined named overview."""
            assert current_scenario == "overview_partial"
            return []

        @tool
        async def search_knowledge_lexical(
            filters: dict[str, Any], limit: int
        ) -> list[dict[str, Any]]:
            """Read authored encyclopedia evidence for the mixed request."""
            assert current_scenario in {"mixed", "overview_partial"} and limit == 1
            path = "fixtures/knowledge/stone-encyclopedias/stone-encyclopedia_en.md"
            chapters = build_encyclopedia_documents((ROOT / path).read_text(), path)
            return [
                document.model_dump(mode="json")
                for document in [*chapters, *guide]
                if filters["stone_type"] in document.stone_types
                and document.model_dump()["document_kind"] == filters["document_kind"]
            ][:limit]

        @tool
        async def get_compatibility_pair(
            first_type: str, second_type: str
        ) -> dict[str, Any] | None:
            """Read the authored rule for one exact type pair."""
            current_calls.append("exact-pair")
            if current_scenario == "missing":
                return None
            pair = pairs[build_pair_key(StoneType(first_type), StoneType(second_type))]
            return pair.model_dump(mode="json")

        @tool
        async def list_compatibility_pairs(stone_type: str, verdict: str) -> list[dict[str, Any]]:
            """Read authored partner lists only for the combined named overview."""
            assert current_scenario == "overview_partial"
            return [
                pair.model_dump(mode="json")
                for pair in pairs.values()
                if stone_type in pair.stone_types and pair.verdict == verdict
            ]

        @tool
        async def search_stones_hybrid(
            lexical_query: str, semantic_query: str, filters: dict[str, Any]
        ) -> dict[str, Any]:
            """Return no candidate cards for the mixed-route regression."""
            current_calls.append("candidate-search")
            return {"candidates": [], "dropped": []}

        search_stones_hybrid.metadata = {"retrieval_calls": 2}

        class PairFixtureModel:
            def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
                def respond(messages: Any) -> dict[str, Any]:
                    if schema is ParseQuestion:
                        output: Any = current_parse
                    elif schema is ToolPlan:
                        output = ToolPlan(
                            tools=current_allowed_tools, reason="Read the exact pair rule"
                        )
                    elif schema is SelectCandidates:
                        output = SelectCandidates(stone_ids=[])
                    elif schema is ReferenceEvidence:
                        data = json.loads(messages[-1].content)
                        current_evidence_inputs.append(data)
                        selected = [
                            source
                            for source in data["sources"]
                            if current_scenario in {"mixed", "overview_partial"}
                            and source["scope"] == "encyclopedia"
                            or current_scenario not in {"mixed", "overview_partial", "no_evidence"}
                        ]
                        output = ReferenceEvidence.model_validate(
                            {
                                "quotes": [
                                    {
                                        "source_id": source["source_id"],
                                        "quote": (
                                            "Verdict: CONDITIONAL"
                                            if current_scenario == "verdict_only"
                                            else source["text"]
                                        ),
                                    }
                                    for source in selected
                                ]
                            }
                        )
                    elif schema is ReferenceAnswer:
                        data = json.loads(messages[-1].content)
                        current_answer_inputs.append(data)
                        output = ReferenceAnswer(
                            sections=[
                                ReferenceSection(
                                    scope=quote["scope"],
                                    explanation=quote["quote"],
                                    source_ids=[quote["source_id"]],
                                )
                                for quote in data["quotes"]
                            ]
                        )
                    else:
                        raise AssertionError(schema)
                    return {
                        "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                        "parsed": output,
                    }

                return RunnableLambda(respond)

        model: Any = PairFixtureModel()
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
            retrieval_tools=[search_stones_hybrid] if scenario_name == "mixed" else [],
            details_tool=get_stone_details,
            status_tool=get_stone_status_by_name,
            timeline_tool=get_case_timeline,
            compatibility_tool=get_compatibility_pair,
            encyclopedia_tool=search_knowledge_lexical,
            reference_tools=ReferenceTools(
                stone_status=get_stone_status_by_name,
                stone_details=get_stone_details,
                timeline=get_case_timeline,
                encyclopedia=search_knowledge_lexical,
                exact_pair=get_compatibility_pair,
                pair_list=list_compatibility_pairs,
            ),
        )

        if scenario_name == "missing":
            assert "GRANITE + GNEISS · `UNKNOWN`" in result["answer"]
            assert not result["sources"] and not evidence_inputs
            return

        pair = pairs[scenario["pair_key"]]
        assert pair.source_key in result["sources"]
        assert any(
            source["source_id"] == pair.source_key and source["text"] == pair.text
            for source in evidence_inputs[0]["sources"]
        )
        assert pair.verdict.value in result["answer"]
        assert "GRANITE + " in result["answer"]
        if scenario_name == "mixed":
            assert "candidate-search" in calls and "exact-pair" in calls
            assert answer_inputs[0]["quotes"]
            assert all(quote["scope"] == "encyclopedia" for quote in answer_inputs[0]["quotes"])
            assert "Original pair rule:" in result["answer"]
            assert pair.text in result["answer"]
        elif scenario_name == "verdict_only":
            assert answer_inputs[0]["quotes"][0]["quote"] == "Verdict: CONDITIONAL"
            assert "Original pair rule:" in result["answer"]
        elif scenario_name == "overview_partial":
            assert all(q["scope"] == "encyclopedia" for q in answer_inputs[0]["quotes"])
            assert "No validated summary for this scope" in result["answer"]
        elif scenario_name == "no_evidence":
            assert pair.text in result["answer"]
            assert result["answer"].count(pair.text) == 1
        else:
            assert any(
                quote["source_id"] == pair.source_key and quote["quote"] == pair.text
                for quote in answer_inputs[0]["quotes"]
            )
        if scenario["pair_key"] == "GRANITE+GRANITE":
            assert "Rotate small decisions" in result["answer"]
            assert "friendly decision deadline" in result["answer"]
            assert result["answer"].count(pair.text) == 1
        if scenario_name == "named":
            assert calls[:2] == ["identity", "exact-pair"]

    for scenario_name, scenario in scenarios.items():
        await run_scenario(scenario_name, scenario)


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
    assert "search_candidates" in mixed_allowed
    assert "get_stone_details" in mixed_allowed
    assert (
        plan_error(
            ToolPlan(tools=mixed_allowed, reason="Cover both requested branches"),
            mixed_allowed,
            request,
        )
        is None
    )


@pytest.mark.asyncio
async def test_reference_and_recommendation_targets_are_explicitly_independent() -> None:
    question = "Tell me about Svetlana and find a quiet companion."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
            "retrieval": {"lexical_query": "quiet", "semantic_query": "quiet companion"},
        }
    )
    request = parsed.resolve_references({1: question})
    assert request.stone_name == "Svetlana"
    assert request.recommendation_name is None

    same_target = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
        }
    )
    same_request = same_target.resolve_references({1: question})
    assert same_request.stone_name == same_request.recommendation_name == "Svetlana"
    allowed = permitted_tools(parsed.resolve({1: question})[0], request)
    assert len(allowed) == 6
    mixed_state: Any = {
        "question": question,
        "tools_used": 0,
        "criteria": parsed.resolve({1: question})[0],
        "reference_request": request,
        "permitted_tools": allowed,
        "tool_plan": ToolPlan(tools=allowed, reason="Read both goals"),
        "plan_status": "accepted",
        "question_fragments": {1: question},
        "result": {
            "answer": "Named individual result",
            "sources": {"individual:1": {}},
            "verified_statuses": {},
        },
    }
    assert workflow.after_planning(mixed_state) == "execute_reference_plan"
    assert workflow.after_reference_answer(mixed_state) == "mixed"
    saved: Any = await workflow.continue_mixed(
        mixed_state, runtime=Runtime(context=cast(Any, None))
    )
    assert saved["reference_component"]["answer"] == "Named individual result"

    parsed_without_name = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requested_care": [{"fragment_id": 1, "stone_type": "OBSIDIAN"}],
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "household_type": "GRANITE",
                    "first_type": None,
                    "target": "candidate",
                }
            ],
        }
    )
    no_name_criteria, _ = parsed_without_name.resolve({1: "Find a companion; care for obsidian."})
    no_name_request = parsed_without_name.resolve_references(
        {1: "Find a companion; care for obsidian."}
    )
    no_name_plan = permitted_tools(no_name_criteria, no_name_request)
    assert no_name_plan == ["search_candidates", "search_knowledge_lexical"]


def test_candidate_compatibility_does_not_become_named_reference_pair() -> None:
    fragments = {
        1: "What does Svetlana like?",
        2: "Recommend one quiet companion compatible with granite.",
    }
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "preferences"},
            "requested_compatibility": [
                {
                    "fragment_id": 2,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "candidate",
                }
            ],
        }
    )
    criteria, _ = parsed.resolve(fragments)
    request = parsed.resolve_references(fragments)
    assert not request.pairs
    assert criteria.requested_compatibility[0].household_type.value == "GRANITE"
    parsed_reference_pair = ParseQuestion.model_validate(
        {
            **parsed.model_dump(),
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "named_stone",
                }
            ],
        }
    )
    assert (
        parsed_reference_pair.resolve_references(fragments).pairs[0].second_type.value == "GRANITE"
    )
    invalid_cases: list[dict[str, Any]] = [
        {
            "recommendation_limit": 0,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": "BASALT",
                    "household_type": "GRANITE",
                    "target": "named_stone",
                }
            ],
        },
        {
            "recommendation_limit": 0,
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "types",
                }
            ],
        },
        {
            "recommendation_limit": 0,
            "requested_compatibility": [
                {
                    "fragment_id": 999,
                    "first_type": "BASALT",
                    "household_type": "GRANITE",
                    "target": "types",
                }
            ],
        },
        {
            "recommendation_limit": 0,
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "named_stone",
                }
            ],
        },
    ]
    for fields in invalid_cases:
        with pytest.raises((KeyError, ValueError)):
            ParseQuestion.model_validate(fields).resolve_references(fragments)


def test_mixed_result_keeps_both_answers_sources_and_statuses() -> None:
    candidate: dict[str, object] = {
        "answer": "Recommended companion.",
        "sources": {"stone-card:one": {"data": {"id": "one"}}},
        "verified_statuses": {"one": "AVAILABLE"},
        "recommended_stone_ids": ["one"],
        "candidate_decisions": [{"stone_id": "one", "outcome": "recommended"}],
    }
    reference: dict[str, object] = {
        "answer": "Svetlana profile. Sources: stone-card:one",
        "sources": {"stone-card:one": {"data": {"id": "different"}}, "encyclopedia:marble": {}},
        "verified_statuses": {"svetlana": "AVAILABLE"},
        "reference_answer_status": "generated",
    }
    result: Any = workflow.combine_mixed_result(candidate, reference, "generated")
    assert "Svetlana profile" in result["answer"]
    assert "Recommended companion" in result["answer"]
    assert "reference:stone-card:one" in result["answer"]
    assert "reference:stone-card:one" in result["sources"]
    assert "encyclopedia:marble" in result["sources"]
    assert result["verified_statuses"] == {"svetlana": "AVAILABLE", "one": "AVAILABLE"}
    assert result["recommended_stone_ids"] == ["one"]


def test_budget_stop_keeps_sources_already_read_for_reference_branch() -> None:
    from stone_shelter_assistant.assistant.reference_lookup import ReferenceResult

    reference = ReferenceResult(
        lines=["No authored encyclopedia care information is available for onyx."],
        sources={"stone-card:svetlana": {"data": {"name": "Svetlana"}}},
        context_sources={
            "stone-card:svetlana": ReferenceSource(
                source_id="stone-card:svetlana", scope="individual", text="Enjoys singing."
            )
        },
    )
    stop_state: Any = {
        "question": "Tell me about Svetlana and recommend a companion.",
        "stop_reason": "budget_limit",
        "reference_result": reference,
    }
    result: Any = workflow.stop(stop_state)["result"]
    assert "No authored encyclopedia care information" in result["answer"]
    assert "Enjoys singing" in result["answer"]
    assert "stone-card:svetlana" in result["sources"]
    assert result["candidate_branch_status"] == "budget_limit"


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
