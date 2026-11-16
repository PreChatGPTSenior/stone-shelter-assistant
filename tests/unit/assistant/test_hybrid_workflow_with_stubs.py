"""Run the real hybrid workflow graph with fixed models, in-memory tools and telemetry."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
)
from stone_shelter_assistant.assistant.question_grounding import (
    GroundingDecision,
    GroundingResponse,
    QuestionCoverageAudit,
)
from stone_shelter_assistant.assistant.reference_evidence import (
    ReferenceAnswer,
    ReferenceEvidence,
    ReferenceQuote,
    ReferenceSection,
)
from stone_shelter_assistant.assistant.reference_lookup import ReferenceTools
from stone_shelter_assistant.assistant.selection import (
    ParseQuestion,
    SelectCandidates,
)
from stone_shelter_assistant.assistant.tools import stone_search_tools
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.search.knowledge.grounding_concept_store_service import (
    GroundingEntry,
    build_grounding_snapshot,
)
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from tests.unit.search.test_rrf import card


def _schema_class(schema: Any) -> type[Any]:
    if isinstance(schema, type):
        return schema
    models = {
        model.__name__: model
        for model in (
            CandidateEvidence,
            GroundingResponse,
            ReferenceAnswer,
            ReferenceEvidence,
            ParseQuestion,
            SelectCandidates,
        )
    }
    return models[schema["title"]]


def payload(span: Any, field: str) -> Any:
    return json.loads(span.attributes[f"langfuse.observation.{field}"])


@pytest.mark.asyncio
@pytest.mark.parametrize("current_status", ["AVAILABLE", "RESERVED", "ADOPTED", "RETURNED", None])
@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-FLOW-02")
@pytest.mark.acceptance("AC-FLOW-03")
@pytest.mark.acceptance("AC-GROUNDING-01")
@pytest.mark.acceptance("AC-RETRIEVAL-01")
@pytest.mark.acceptance("AC-AVAILABILITY-01")
@pytest.mark.acceptance("AC-DECISION-01")
@pytest.mark.acceptance("AC-ANSWER-01")
async def test_full_hybrid_graph_preserves_provenance_and_decisions(
    current_status: str | None,
) -> None:
    snapshot = json.loads(
        (Path(__file__).parents[3] / "fixtures/assistant/quiet-home-assessment.json").read_text()
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
        if current_status is None:
            return []
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
        """Return history that deliberately disagrees with the current status."""
        if case_external_id == reference_details["shelter_case"]["external_id"]:
            return []
        assert case_external_id == details["shelter_case"]["external_id"]
        historical_event = "ADOPTED" if current_status == "AVAILABLE" else "MADE_AVAILABLE"
        return [
            {
                "event_external_id": "f74439ed-c9d5-4d07-958f-6c28eaf8c166",
                "event_type": historical_event,
                "occurred_at": "2025-01-01T00:00:00+00:00",
                "event_notes": "Historical availability event; current status comes from PostgreSQL.",
            }
        ]

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
                {
                    "fragment_id": 1,
                    "question_quote": "Tell me what Madame Obsidian likes and find one quiet stone.",
                    "fact_type": "decision_rotation_agreed",
                    "value": False,
                }
            ],
            "requirements": {
                "character": [{"fragment_id": 1, "question_quote": "quiet stone"}],
                "compatibility": [],
            },
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
            ],
            question_coverage=QuestionCoverageAudit(
                status="complete", summary="All parsed fixture atoms are represented."
            ),
        ),
        ParseQuestion: parsed,
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
                        "criterion_id": "requirement.character.1",
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
            schema_model = _schema_class(schema)
            if schema_model is ReferenceEvidence:

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
            if schema_model is ReferenceAnswer:

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
            parsed_output = outputs[cast(type[BaseModel], schema_model)]

            def fixture_response(_: Any) -> dict[str, Any]:
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": parsed_output,
                }

            return RunnableLambda(fixture_response, name="fixture_model")

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
                models=workflow.WorkflowModels(
                    selection_model=model,
                    selection_uses_json_schema=True,
                    parsing_model=model,
                    evaluation_model=model,
                    evaluation_uses_json_schema=True,
                    answer_model=model,
                ),
                tools=workflow.WorkflowTools(
                    retrieval=tuple(search_tools),
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
                ),
                grounding_catalog=AsyncMock(
                    load=AsyncMock(
                        return_value=build_grounding_snapshot(
                            [
                                GroundingEntry.model_validate(e)
                                for e in json.loads(
                                    (
                                        Path(__file__).parents[3]
                                        / "fixtures/knowledge/grounding/grounding_en-v1.json"
                                    ).read_text()
                                )
                            ],
                            "en",
                            "en-v1",
                        )
                    )
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
        if current_status is None:
            assert sid not in verified_statuses
        else:
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
        assert "Typesense #1" in hit["explanation"]
        decisions = payload(by_name["select_candidates"], "output")["selection_decisions"]
        assert {item["stone_id"]: item["selected"] for item in decisions} == {
            sid: True,
            str(b.id): False,
        }
        verified = payload(by_name["verify"], "output")["verified_statuses"]
        if current_status is None:
            assert sid not in verified
        else:
            assert verified[sid] == current_status
        evaluation = payload(by_name["evaluate_candidates"], "output")["candidate_evaluations"][0]
        assert evaluation["stone_id"] == sid
        assert evaluation["eligible"] == (current_status == "AVAILABLE")
        assert not any(span.name.startswith(("Runnable", "after_")) for span in spans)
    finally:
        client.shutdown()
