"""Check observation loading and event provenance through assessment and answer functions."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails


@pytest.mark.asyncio
@pytest.mark.parametrize("compatibility_only", [False, True])
@pytest.mark.acceptance("AC-EVIDENCE-01")
@pytest.mark.acceptance("AC-EVIDENCE-02")
@pytest.mark.acceptance("AC-DECISION-01")
@pytest.mark.acceptance("AC-ANSWER-01")
async def test_candidate_assessment_loads_svetlana_observations_with_event_provenance(
    monkeypatch: pytest.MonkeyPatch, compatibility_only: bool
) -> None:
    fixture = json.loads(
        (
            Path(__file__).parents[3] / "fixtures/stones/b19266ec-28a2-4fd3-851b-7fad50b6e175.json"
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
            "criterion_id": "requirement.character.1",
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
                    "criterion_id": "requirement.character.1",
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
                else [
                    {
                        "criterion_id": "requirement.character.1",
                        "fragment_id": 1,
                        "question_quote": "Must stay quiet in the morning.",
                    }
                ],
                "compatibility": [],
            },
            "preferences": {
                "character": [],
                "compatibility": [
                    {
                        "criterion_id": "preference.compatibility.1",
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
                tools=SimpleNamespace(
                    compatibility_tool=None,
                    encyclopedia_tool=None,
                    timeline_tool=timeline,
                ),
                models=SimpleNamespace(
                    evaluation_model=None,
                    evaluation_uses_json_schema=True,
                    evaluation_reasoning=None,
                ),
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
                tools=SimpleNamespace(
                    details_tool=SimpleNamespace(name="get_stone_details"),
                    compatibility_tool=SimpleNamespace(name="get_compatibility_pair"),
                ),
                models=SimpleNamespace(answer_model=None, evaluation_reasoning=None),
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
