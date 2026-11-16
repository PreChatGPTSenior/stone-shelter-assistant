"""Opt-in Jev choice-model calibration; offline tests never call the network."""

import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

from tests.synthetic_evaluation.model_calibration.jev_calibration import (
    LABELS,
    decision_payload,
    fixture_hashes,
    load_cases,
    select_cases,
    validate_response,
)

ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sanitize_response(response: Any, api_key: str) -> dict[str, Any]:
    """Keep only documented output fields; never archive arbitrary response text."""
    if not isinstance(response, dict):
        return {"shape": type(response).__name__}
    safe: dict[str, Any] = {}

    def safe_text(value: Any, limit: int = 120) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        return value.replace(api_key, "[redacted]")[:limit]

    model = response.get("model")
    if (safe_model := safe_text(model)) is not None:
        safe["model"] = safe_model
    for key in ("id", "provider"):
        if (value := safe_text(response.get(key))) is not None:
            safe[key] = value
    answers = response.get("answers")
    if isinstance(answers, dict):
        answer = answers.get("evidence_verdict")
        if (
            isinstance(answer, dict)
            and answer.get("type") == "choice"
            and answer.get("choice") in LABELS
            and isinstance(answer.get("confidence"), (int, float))
            and not isinstance(answer.get("confidence"), bool)
            and math.isfinite(answer["confidence"])
            and 0 <= answer["confidence"] <= 1
        ):
            probabilities = answer.get("probabilities")
            if (
                isinstance(probabilities, dict)
                and set(probabilities) == set(LABELS)
                and all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and 0 <= value <= 1
                    for value in probabilities.values()
                )
            ):
                safe["answers"] = {
                    "evidence_verdict": {
                        "type": "choice",
                        "choice": answer["choice"],
                        "confidence": answer["confidence"],
                        "probabilities": probabilities,
                    }
                }
    usage = response.get("usage")
    if (
        isinstance(usage, dict)
        and all(
            isinstance(usage.get(key), int) and not isinstance(usage[key], bool) and usage[key] >= 0
            for key in ("input_tokens", "output_tokens")
        )
        and isinstance(usage.get("cost"), (int, float))
        and not isinstance(usage["cost"], bool)
        and math.isfinite(usage["cost"])
        and usage["cost"] >= 0
    ):
        safe["usage"] = {key: usage[key] for key in ("input_tokens", "output_tokens", "cost")}
    return safe


@pytest.mark.parametrize("case_index", range(6))
def test_fixture_case_payload_excludes_expected_rationale(case_index: int) -> None:
    _, cases = load_cases()
    case = cases[case_index]
    payload = decision_payload("jev-test-model", case)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["questions"]["evidence_verdict"]["type"] == "choice"
    assert set(payload["questions"]["evidence_verdict"]["criteria"]) == set(LABELS)
    assert case["claim"] in serialized
    assert '"expected_label"' not in serialized
    assert '"rationale"' not in serialized
    assert case["rationale"] not in serialized
    assert all(source["source_id"] in serialized for source in case["sources"])


def test_reviewed_fixture_cases_preserve_scope_and_evidence_ids() -> None:
    _, cases = load_cases()
    assert [case["expected_label"] for case in cases] == [
        "INSUFFICIENT_EVIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "SUPPORTED",
        "CONTRADICTED",
        "CONFLICTING_EVIDENCE",
    ]
    event = cases[0]["sources"][1]["text"]
    assert "94156b7f-cc92-4d65-861e-bd87e8662fb5" in event
    assert "2026-11-02T05:00:00+04:00" in event
    assert "singing loudly on a windowsill" in cases[0]["sources"][0]["text"]
    assert "No individual profile is present" in cases[1]["sources"][1]["text"]
    assert "It likes a predictable household." in cases[1]["sources"][2]["text"]
    assert "basalt-gneiss pair" in cases[2]["sources"][0]["text"]
    assert "compatibility:granite+granite" in cases[2]["sources"][1]["text"]
    assert "A thoughtful stone who enjoys quiet evenings." in cases[3]["sources"][0]["text"]
    assert "Becomes anxious around vacuum cleaners." in cases[4]["sources"][0]["text"]
    conflict = cases[5]
    assert conflict["provenance"] == "mixed_authored_fixture_and_synthetic_calibration_source"
    assert conflict["sources"][0]["provenance"] == "authored_fixture"
    witness = conflict["sources"][1]
    assert witness["provenance"] == "synthetic_calibration_only"
    assert witness["source_id"] != conflict["sources"][0]["source_id"]
    assert "same supervised settling-in session" in witness["provenance_note"]
    payload = decision_payload("jev-test-model", conflict)
    evidence = payload["state"]["evidence"]
    assert "same supervised settling-in session" in evidence[1]["provenance_note"]
    assert "did not remain calm" in evidence[1]["text"]


def test_case_selection_accepts_new_cases_and_rejects_invalid_ids() -> None:
    _, cases = load_cases()
    selected = select_cases(
        cases,
        "sir-pebble-quiet-evenings, madame-obsidian-vacuum-anxiety, quartzless-synthetic-same-session-conflict",
    )
    assert [case["id"] for case in selected] == [
        "sir-pebble-quiet-evenings",
        "madame-obsidian-vacuum-anxiety",
        "quartzless-synthetic-same-session-conflict",
    ]
    for invalid in (
        "",
        "sir-pebble-quiet-evenings,",
        "sir-pebble-quiet-evenings,sir-pebble-quiet-evenings",
        "missing-case",
    ):
        with pytest.raises(ValueError):
            select_cases(cases, invalid)


def test_response_requires_complete_choice_probabilities_and_usage() -> None:
    answer = validate_response(
        {
            "model": "jev-test-model",
            "answers": {
                "evidence_verdict": {
                    "type": "choice",
                    "choice": "INSUFFICIENT_EVIDENCE",
                    "confidence": 0.8,
                    "probabilities": {
                        "SUPPORTED": 0.05,
                        "CONTRADICTED": 0.05,
                        "CONFLICTING_EVIDENCE": 0.1,
                        "INSUFFICIENT_EVIDENCE": 0.8,
                    },
                }
            },
            "usage": {"input_tokens": 100, "output_tokens": 12, "cost": 0.00001},
        }
    )
    assert answer["choice"] == "INSUFFICIENT_EVIDENCE"

    with pytest.raises(ValueError, match="exactly the four labels"):
        validate_response(
            {
                "model": "jev-test-model",
                "answers": {
                    "evidence_verdict": {
                        "type": "choice",
                        "choice": "SUPPORTED",
                        "confidence": 0.9,
                        "probabilities": {"SUPPORTED": 1.0},
                    }
                },
                "usage": {"input_tokens": 1, "output_tokens": 1, "cost": 0.0},
            }
        )


def test_archived_response_sanitization_redacts_credentials_and_nested_extras() -> None:
    api_key = "fake-key-for-redaction-test"
    safe = _sanitize_response(
        {
            "model": f"jev-{api_key}",
            "answers": {
                "evidence_verdict": {
                    "type": "choice",
                    "choice": "SUPPORTED",
                    "confidence": 0.9,
                    "probabilities": {
                        "SUPPORTED": 0.9,
                        "CONTRADICTED": 0.03,
                        "CONFLICTING_EVIDENCE": 0.02,
                        "INSUFFICIENT_EVIDENCE": 0.05,
                        "extra": api_key,
                    },
                    "vendor_debug": api_key,
                }
            },
            "usage": {"input_tokens": 50, "output_tokens": True},
            "debug": api_key,
        },
        api_key,
    )
    serialized = json.dumps(safe)
    assert api_key not in serialized
    assert safe["model"] == "jev-[redacted]"
    assert "answers" not in safe
    assert "usage" not in safe

    safe = _sanitize_response(
        {
            "model": "typesafe/jev-1.14-20261014",
            "id": api_key,
            "provider": "TypeSafe",
            "usage": {"input_tokens": 50, "output_tokens": 8, "cost": 0.000002},
        },
        api_key,
    )
    assert safe == {
        "model": "typesafe/jev-1.14-20261014",
        "id": "[redacted]",
        "provider": "TypeSafe",
        "usage": {"input_tokens": 50, "output_tokens": 8, "cost": 0.000002},
    }


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_JEV_MODEL_CALIBRATION") != "1",
    reason="Explicit Jev model calibration opt-in required",
)
async def test_run_jev_model_calibration() -> None:
    load_dotenv(ROOT / ".env", override=False)
    model = os.getenv("JEV_MODEL")
    api_key = os.getenv("OPENROUTER_API_KEY")
    assert model, "Select JEV_MODEL explicitly before authorizing calls"
    assert api_key, "Set OPENROUTER_API_KEY in the environment or project .env"
    _, all_cases = load_cases()
    selection = (
        os.getenv("JEV_CALIBRATION_CASE_IDS") if "JEV_CALIBRATION_CASE_IDS" in os.environ else None
    )
    cases = select_cases(all_cases, selection)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "test-evaluation-results/jev-model-calibration" / run_id
    output.mkdir(parents=True, exist_ok=False)
    hashes = fixture_hashes(cases)
    code_paths = [Path(__file__), Path(__file__).with_name("jev_calibration.py")]
    code_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in code_paths
    }
    result: dict[str, Any] = {
        "suite_id": "jev-evidence-calibration-en-v1",
        "run_id": run_id,
        "status": "running",
        "endpoint": "https://openrouter.ai/api/alpha/decisions",
        "model_requested": model,
        "fixture_hashes": hashes,
        "code_hashes": code_hashes,
        "case_count": len(cases),
        "total_case_count": len(all_cases),
        "selected_case_ids": [case["id"] for case in cases],
        "cases": [],
        "limitation": "Six reviewed cases provide a small calibration set. One case mixes authored fixture evidence with an explicitly synthetic calibration-only witness; results do not establish broad judge performance.",
    }
    _write_json(output / "result.json", result)
    mismatches: list[str] = []
    technical_failure = False
    for case in cases:
        payload = decision_payload(model, case)
        record: dict[str, Any] = {
            "case_id": case["id"],
            "claim": case["claim"],
            "provenance": case.get("provenance", "fixture_only"),
            "source_provenance": [
                {
                    "source_id": source["source_id"],
                    "provenance": source.get("provenance", "authored_fixture"),
                }
                for source in case["sources"]
            ],
            "expected_label": case["expected_label"],
            "reviewed_rationale": case["rationale"],
            "request": payload,
            "request_sha256": hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
        }
        request = urllib.request.Request(
            "https://openrouter.ai/api/alpha/decisions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        parsed: Any = None
        body: bytes | None = None
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read()
                parsed = json.loads(body)
                answer = validate_response(parsed)
                observed = answer["choice"]
                record.update(
                    {
                        "status": "completed",
                        "response": _sanitize_response(parsed, api_key),
                        "response_sha256": hashlib.sha256(body).hexdigest(),
                        "matches_expected": observed == case["expected_label"],
                    }
                )
                if observed != case["expected_label"]:
                    mismatches.append(case["id"])
        except Exception as error:
            try:
                error_body = error.read(2048) if isinstance(error, urllib.error.HTTPError) else b""
            except Exception:
                error_body = b""
            diagnostic = error_body.decode("utf-8", errors="replace") if error_body else str(error)
            diagnostic = diagnostic.replace(api_key, "[redacted]")[:400]
            record.update(
                {
                    "status": "technical_error",
                    "error_type": type(error).__name__,
                    "diagnostic": diagnostic or "Request or response processing failed.",
                    "response": _sanitize_response(parsed, api_key) if parsed is not None else None,
                    "response_sha256": (
                        hashlib.sha256(body or error_body).hexdigest()
                        if body or error_body
                        else None
                    ),
                }
            )
            if isinstance(error, urllib.error.HTTPError):
                record["http_status"] = error.code
            technical_failure = True
        result["cases"].append(record)
        _write_json(output / "result.json", result)
        if technical_failure:
            break
    result["status"] = (
        "technical_error"
        if technical_failure
        else "completed"
        if not mismatches and all(item["status"] == "completed" for item in result["cases"])
        else "calibration_failed"
    )
    result["mismatches"] = mismatches
    _write_json(output / "result.json", result)
    _write_json(
        output / "manifest.json",
        {
            key: result[key]
            for key in (
                "suite_id",
                "run_id",
                "status",
                "endpoint",
                "model_requested",
                "fixture_hashes",
                "code_hashes",
                "case_count",
                "total_case_count",
                "selected_case_ids",
                "limitation",
                "mismatches",
            )
        },
    )
    assert result["status"] == "completed", (
        f"Jev calibration did not match reviewed labels; see {output}"
    )
