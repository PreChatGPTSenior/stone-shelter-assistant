"""Opt-in paid GEval of a captured candidate-evidence call from a full-run result.json.

Requires RUN_SAVED_RUN_GEVAL=1, SAVED_GEVAL_RESULT_PATH, and
OPENROUTER_GEVAL_MODEL. It grades only saved model input/output and never reruns
the workflow. The quiet-home rubric requires a matching criterion in the capture.
The test asserts that judging completed; its 0.8 pass flag is an uncalibrated
diagnostic, not a quality gate.
"""

import hashlib
import json
import os
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
pytest.importorskip("deepeval", reason="Install the eval dependency group for DeepEval")
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from langfuse import Langfuse
from pydantic import ValidationError

from stone_shelter_assistant.assistant.candidate_evidence import CandidateEvidence
from stone_shelter_assistant.assistant.tracing import provider_error_details
from stone_shelter_assistant.core.settings import LangfuseSettings, OpenRouterSettings
from tests.evaluation.support.geval_judge import (
    GEVAL_NAME,
    GEVAL_STEPS,
    GEVAL_THRESHOLD,
    OpenRouterJudge,
)
from tests.evaluation.support.geval_sources import restore_recorded_sources

ROOT = Path(__file__).resolve().parents[2]


def _decoded(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _capture(
    result: dict[str, Any], observations: dict[str, Any]
) -> tuple[Any, Any, dict[str, Any], Any]:
    """Select the captured candidate-evidence generation and preserve its exact payloads."""
    entries = observations.get("observations")
    if not isinstance(entries, list):
        raise ValueError("Saved observations.json has no observations list")
    stage_ids = {
        item.get("id")
        for item in entries
        if isinstance(item, dict) and item.get("name") == "evaluate_candidates"
    }
    generations = [
        item
        for item in entries
        if isinstance(item, dict)
        and item.get("type") == "GENERATION"
        and item.get("parentObservationId") in stage_ids
    ]
    if len(generations) != 1:
        raise ValueError(
            f"Expected one captured evaluate_candidates generation, found {len(generations)}"
        )
    generation = generations[0]
    source_trace_id = result.get("trace_id")
    stage = next(
        (
            item
            for item in entries
            if isinstance(item, dict) and item.get("id") == generation.get("parentObservationId")
        ),
        None,
    )
    if (
        not isinstance(source_trace_id, str)
        or not isinstance(stage, dict)
        or stage.get("traceId") != source_trace_id
        or generation.get("traceId") != source_trace_id
    ):
        raise ValueError(
            "Saved result and candidate-evidence observations do not share one traceId"
        )
    request = _decoded(generation.get("input"))
    response = _decoded(generation.get("output"))
    assessment = _assessment_payload(response)
    if request is None:
        raise ValueError("Captured generation is missing its actual input or assessment output")
    if result.get("status") != "completed" or not isinstance(result.get("graph_state"), dict):
        raise ValueError("GEval requires a completed current full-run result with graph_state")
    if result["graph_state"].get("assessment_status") != "parsed":
        raise ValueError("GEval requires an assessment parsed by the current workflow")
    trace_entries = [
        item
        for item in entries
        if isinstance(item, dict) and item.get("traceId") == source_trace_id
    ]
    resolved_request = restore_recorded_sources(request, trace_entries)
    _validate_source_quotes(resolved_request, assessment)
    return request, assessment, generation, resolved_request


def _assessment_payload(response: Any) -> dict[str, Any]:
    """Decode either current structured-output representation, then validate its DTO."""
    payload: Any = None
    if isinstance(response, dict):
        if "content" in response:
            payload = _decoded(response["content"])
        calls = response.get("tool_calls")
        if calls is None and isinstance(response.get("additional_kwargs"), dict):
            calls = response["additional_kwargs"].get("tool_calls")
        if not payload and isinstance(calls, list) and len(calls) == 1:
            call = calls[0]
            if isinstance(call, dict):
                payload = _decoded(call.get("args"))
                if payload is None and isinstance(call.get("function"), dict):
                    payload = _decoded(call["function"].get("arguments"))
    if not isinstance(payload, dict):
        raise ValueError(
            "Captured candidate-evidence output is not a supported current structured result"
        )
    try:
        return CandidateEvidence.model_validate(payload).model_dump(mode="json")
    except ValidationError as error:
        raise ValueError(
            "Captured candidate-evidence output fails the current CandidateEvidence contract"
        ) from error


def _assert_quiet_home_scope(request: Any) -> None:
    messages = request if isinstance(request, list) else []
    user_contents = [
        message.get("content")
        for message in messages
        if isinstance(message, dict) and message.get("role") in {"user", "human"}
    ]
    found = False
    for content in user_contents:
        value = _decoded(content)
        if isinstance(value, dict):
            criteria = value.get("character_criteria", [])
            if isinstance(criteria, list) and any(
                "quiet" in json.dumps(item, ensure_ascii=False).casefold() for item in criteria
            ):
                found = True
    if not found:
        raise ValueError(
            "The captured candidate-evidence request has no quiet-home criterion for this rubric"
        )


def _validate_source_quotes(request: Any, assessment: dict[str, Any]) -> None:
    """Bind every scored quote to the exact source text captured in the model request."""
    messages = request if isinstance(request, list) else []
    human = [
        _decoded(message.get("content"))
        for message in messages
        if isinstance(message, dict) and message.get("role") in {"user", "human"}
    ]
    if len(human) != 1 or not isinstance(human[0], dict):
        raise ValueError("Captured candidate-evidence input must contain one current user payload")
    sources = human[0].get("candidate_sources")
    if not isinstance(sources, list):
        raise ValueError("Captured candidate-evidence input has no candidate_sources list")
    keyed = {}
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Captured candidate source is malformed")
        key = (
            source.get("stone_id"),
            source.get("source_ref"),
            source.get("observation_external_id"),
        )
        if key in keyed:
            raise ValueError(f"Ambiguous captured candidate source reference: {key}")
        keyed[key] = source.get("text")
    for category in ("character", "individual_compatibility"):
        for finding in assessment[category]:
            key = (
                finding["stone_id"],
                finding["source_ref"],
                finding.get("observation_external_id"),
            )
            text = keyed.get(key)
            if not isinstance(text, str) or not finding["quote"] or finding["quote"] not in text:
                raise ValueError(
                    f"Captured assessment quote does not bind to one supplied source: {key}"
                )


def _write_checkpoint(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


@pytest.mark.skipif(
    os.getenv("RUN_SAVED_RUN_GEVAL") != "1" or not os.getenv("SAVED_GEVAL_RESULT_PATH"),
    reason="Explicit paid GEval opt-in and SAVED_GEVAL_RESULT_PATH are required",
)
@pytest.mark.asyncio
async def test_saved_run_candidate_evidence_geval() -> None:
    source = Path(os.environ["SAVED_GEVAL_RESULT_PATH"]).resolve()
    observation_path = source.with_name("observations.json")
    source_bytes = source.read_bytes()
    observation_bytes = observation_path.read_bytes()
    result = json.loads(source_bytes)
    observations = json.loads(observation_bytes)
    request, assessment, generation, resolved_request = _capture(result, observations)
    _assert_quiet_home_scope(resolved_request)

    judge_model = os.getenv("OPENROUTER_GEVAL_MODEL")
    if not judge_model:
        raise ValueError("Set OPENROUTER_GEVAL_MODEL explicitly before enabling paid GEval")
    trace_id = result.get("trace_id")
    run_record: dict[str, Any] = {
        "status": "prepared",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "source_result": str(source),
        "source_result_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_observations": str(observation_path),
        "source_observations_sha256": hashlib.sha256(observation_bytes).hexdigest(),
        "source_trace_id": trace_id,
        "case_id": result["case_id"],
        "judge_settings": {
            "model": judge_model,
            "max_tokens": 4096,
            "max_retries": 0,
            "request_timeout": 120_000,
            "reasoning_effort": "medium",
            "threshold": GEVAL_THRESHOLD,
            "threshold_calibrated": False,
            "metric_name": GEVAL_NAME,
            "evaluation_steps": GEVAL_STEPS,
            "deepeval_version": package_version("deepeval"),
        },
        "evaluation_code_sha256": {
            "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "judge_support": hashlib.sha256(
                (ROOT / "tests/evaluation/support/geval_judge.py").read_bytes()
            ).hexdigest(),
            "source_restore_support": hashlib.sha256(
                (ROOT / "tests/evaluation/support/geval_sources.py").read_bytes()
            ).hexdigest(),
        },
        "captured_generation_id": generation.get("id"),
        "captured_input": request,
        "resolved_judge_input": resolved_request,
        "captured_generation_output": _decoded(generation.get("output")),
        "captured_assessment": assessment,
        "captured_input_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "resolved_judge_input_sha256": hashlib.sha256(
            json.dumps(resolved_request, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "captured_assessment_sha256": hashlib.sha256(
            json.dumps(assessment, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "judge_results": [],
    }
    output = source.with_name(f"{source.stem}-geval-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.json")
    _write_checkpoint(output, run_record)

    attach_score = os.getenv("GEVAL_ATTACH_LANGFUSE") == "1"
    try:
        openrouter = OpenRouterSettings()
        if attach_score and not trace_id:
            raise ValueError("GEVAL_ATTACH_LANGFUSE=1 requires a source trace_id")
        client = None
        if attach_score:
            langfuse = LangfuseSettings()
            client = Langfuse(
                public_key=langfuse.public_key,
                secret_key=langfuse.secret_key.get_secret_value(),
                base_url=langfuse.base_url,
            )
    except Exception as error:
        run_record.update(status="setup_failed", error_type=type(error).__name__)
        _write_checkpoint(output, run_record)
        raise RuntimeError(f"GEval setup failed; checkpoint: {output}") from error
    if attach_score:
        assert client is not None
        with client.start_as_current_observation(
            name=GEVAL_NAME,
            trace_context={"trace_id": trace_id},
        ) as span:
            run_record["judge_results"] = await _evaluate(
                resolved_request,
                assessment,
                judge_model,
                openrouter.api_key.get_secret_value(),
                client,
            )
            _write_checkpoint(output, run_record)
            if run_record["judge_results"].get("status") != "completed":
                _raise_judge_failure(run_record, output)
            try:
                span.update(
                    input={"source_result": str(source)}, output=run_record["judge_results"]
                )
            except Exception as error:
                run_record["telemetry_error_type"] = type(error).__name__
    else:
        run_record["judge_results"] = await _evaluate(
            resolved_request, assessment, judge_model, openrouter.api_key.get_secret_value(), None
        )
        _write_checkpoint(output, run_record)
        if run_record["judge_results"].get("status") != "completed":
            _raise_judge_failure(run_record, output)
    score = run_record["judge_results"]
    import asyncio

    if attach_score:
        assert client is not None
        try:
            client.create_score(
                trace_id=trace_id,
                name=GEVAL_NAME,
                value=score["score"],
                comment=score.get("reason"),
            )
            await asyncio.to_thread(client.flush)
        except Exception as error:
            run_record["telemetry_error_type"] = type(error).__name__
    run_record["status"] = "completed"
    _write_checkpoint(output, run_record)
    print(f"Saved GEval result: {output}")


async def _evaluate(
    request: Any, assessment: Any, model: str, api_key: str, client: Any
) -> dict[str, Any]:
    judge: OpenRouterJudge | None = None
    try:
        judge = OpenRouterJudge(model, api_key, client)
        metric = GEval(
            name=GEVAL_NAME,
            model=judge,
            threshold=GEVAL_THRESHOLD,
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            evaluation_steps=GEVAL_STEPS,
        )
        await metric.a_measure(
            LLMTestCase(
                input=json.dumps(request, ensure_ascii=False),
                actual_output=json.dumps(assessment, ensure_ascii=False),
            )
        )
        if metric.score is None:
            raise RuntimeError("DeepEval completed without returning a score")
    except Exception as error:
        return {
            "status": "judge_failed",
            "error_type": type(error).__name__,
            "provider_error": provider_error_details(error),
            "judge_calls": judge.calls if judge is not None else [],
        }
    return {
        "status": "completed",
        "score": metric.score,
        "reason": metric.reason,
        "passed": metric.is_successful(),
        "judge_model": model,
        "judge_calls": judge.calls,
    }


def _raise_judge_failure(run_record: dict[str, Any], output: Path) -> None:
    run_record["status"] = "judge_failed"
    run_record["error_type"] = run_record["judge_results"].get("error_type", "JudgeFailure")
    run_record["provider_error"] = run_record["judge_results"].get("provider_error")
    _write_checkpoint(output, run_record)
    raise RuntimeError(f"GEval judge failed; checkpoint: {output}")
