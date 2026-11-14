"""Offline validation of captured GEval preparation; no judge calls occur here."""

from typing import Any

import pytest

from tests.evaluation.test_saved_run_geval import (
    _assessment_payload,
    _capture,
    _validate_source_quotes,
)


def _request() -> list[dict[str, object]]:
    return [
        {
            "role": "user",
            "content": {
                "character_criteria": [
                    {"criterion_id": "quiet", "fragment_id": 1, "text": "quiet home"}
                ],
                "candidate_sources": [
                    {
                        "stone_id": "stone-a",
                        "source_ref": "biography",
                        "text": "Enjoys quiet evenings.",
                    }
                ],
            },
        }
    ]


def _evidence() -> dict[str, Any]:
    return {
        "character": [
            {
                "stone_id": "stone-a",
                "source_ref": "biography",
                "finding": "confirmed",
                "quote": "Enjoys quiet evenings.",
                "criterion_id": "quiet",
                "fragment_id": 1,
                "observation_external_id": None,
            }
        ],
        "individual_compatibility": [],
    }


def test_capture_reads_current_langfuse_export_parent_and_json_schema_output() -> None:
    request = _request()
    result = {
        "status": "completed",
        "case_id": "Q18",
        "trace_id": "trace-a",
        "graph_state": {"assessment_status": "parsed"},
    }
    observations = {
        "observations": [
            {"id": "stage", "name": "evaluate_candidates", "type": "SPAN", "traceId": "trace-a"},
            {
                "id": "generation",
                "parentObservationId": "stage",
                "type": "GENERATION",
                "traceId": "trace-a",
                "input": request,
                "output": {"content": _evidence()},
            },
        ]
    }
    captured_request, assessment, generation, resolved_request = _capture(result, observations)
    assert captured_request == request
    assert generation["id"] == "generation"
    assert assessment["character"][0]["quote"] == "Enjoys quiet evenings."
    _validate_source_quotes(resolved_request, assessment)


def test_capture_rejects_observations_from_another_trace() -> None:
    result = {
        "status": "completed",
        "case_id": "Q18",
        "trace_id": "trace-a",
        "graph_state": {"assessment_status": "parsed"},
    }
    observations = {
        "observations": [
            {"id": "stage", "name": "evaluate_candidates", "type": "SPAN", "traceId": "trace-b"},
            {
                "id": "generation",
                "parentObservationId": "stage",
                "type": "GENERATION",
                "traceId": "trace-b",
                "input": _request(),
                "output": {"content": _evidence()},
            },
        ]
    }
    with pytest.raises(ValueError, match="do not share one traceId"):
        _capture(result, observations)


def test_assessment_payload_supports_current_function_calling_output() -> None:
    assessment = _assessment_payload({"content": "", "tool_calls": [{"args": _evidence()}]})
    assert assessment["character"][0]["source_ref"] == "biography"


def test_source_quote_must_match_captured_source_text() -> None:
    assessment = _evidence()
    assessment["character"][0]["quote"] = "The stone is sociable."
    with pytest.raises(ValueError, match="does not bind"):
        _validate_source_quotes(_request(), assessment)


def test_source_reference_cannot_resolve_from_another_trace() -> None:
    request = [
        {
            "role": "user",
            "content": {
                "character_criteria": [
                    {"criterion_id": "quiet", "fragment_id": 1, "text": "quiet home"}
                ],
                "candidate_sources": [
                    {
                        "stone_id": "stone-a",
                        "source_ref": "biography",
                        "text": {"source_ref": "doc-key", "observation_id": "other-source"},
                    }
                ],
            },
        }
    ]
    result = {
        "status": "completed",
        "case_id": "Q04",
        "trace_id": "trace-a",
        "graph_state": {"assessment_status": "parsed"},
    }
    observations = {
        "observations": [
            {"id": "stage", "name": "evaluate_candidates", "type": "CHAIN", "traceId": "trace-a"},
            {
                "id": "generation",
                "parentObservationId": "stage",
                "type": "GENERATION",
                "traceId": "trace-a",
                "input": request,
                "output": {"content": _evidence()},
            },
            {
                "id": "other-source",
                "traceId": "trace-b",
                "output": {"source_key": "doc-key", "text": "Enjoys quiet evenings."},
            },
        ]
    }
    with pytest.raises(ValueError, match="No archived observation"):
        _capture(result, observations)


def test_judge_model_name_survives_deepeval_model_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.evaluation.support import geval_judge

    loaded_model = object()
    monkeypatch.setattr(geval_judge, "ChatOpenRouter", lambda **kwargs: loaded_model)
    judge = geval_judge.OpenRouterJudge("openai/gpt-5.6-terra", "unused-test-key", None)
    assert judge.get_model_name() == "openai/gpt-5.6-terra"
    assert judge.load_model() is loaded_model
