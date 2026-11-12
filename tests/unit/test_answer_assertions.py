"""Assertion grading contracts and adversarial calibration data; no model calls."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError
from tests.evaluation.answer_assertions import (
    AnswerAssessment,
    AnswerSample,
    AssertionCase,
    AssertionFinding,
    EvidenceQuote,
    assessment_messages,
    assessment_report,
    calibration_metrics,
    load_case_sources,
    structural_citations_pass,
)
from tests.live.test_reference_answer_assertions import (
    _archive_judge_result,
    _capture_telemetry,
)

ROOT = Path(__file__).parents[2]
BANK = ROOT / "tests/fixtures/agent-eval/reference-answer-assertions/cases.json"
CASES = [AssertionCase.model_validate(c) for c in json.loads(BANK.read_text())["cases"]]


def fixture_assessment(case: AssertionCase, sample: AnswerSample) -> AnswerAssessment:
    sources = {s.source_id: s for s in load_case_sources(case, ROOT)}
    return AnswerAssessment(
        findings=[
            AssertionFinding(
                assertion_id=a.id,
                verdict="pass"
                if sample.expected[a.id]
                else "missing"
                if a.kind == "requirement"
                else "unsupported",
                reason="Fixture verdict tests binding/reporting, not model reasoning.",
                answer_quote=sample.answer_text() if sample.answer_text() else None,
                evidence=[
                    EvidenceQuote(source_id=a.source_ids[0], quote=sources[a.source_ids[0]].text)
                ],
            )
            for a in case.assertions
        ]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_calibration_has_valid_sources_good_and_bad_answers(case: AssertionCase) -> None:
    sources = load_case_sources(case, ROOT)
    ids = {a.id for a in case.assertions}
    assert len(ids) == len(case.assertions)
    assert any(a.kind == "requirement" for a in case.assertions)
    assert all(set(a.source_ids) <= {s.source_id for s in sources} for a in case.assertions)
    assert any(all(sample.expected.values()) for sample in case.samples)
    assert any(not all(sample.expected.values()) for sample in case.samples)
    for sample in case.samples:
        assert set(sample.expected) == ids
        # Deliberately wrong meaning can still pass the unchanged structural validator.
        assert structural_citations_pass(sample, sources)
        result = assessment_report(case, sample, sources, fixture_assessment(case, sample))
        assert result["overall_status"] == ("pass" if all(sample.expected.values()) else "fail")
        payload = json.loads(cast(str, assessment_messages(case, sample, sources)[-1].content))
        assert "expected" not in payload and "samples" not in payload and "sample_id" not in payload
        assert payload["answer"] == sample.answer_text()


@pytest.mark.parametrize(
    "failure",
    [
        "missing_id",
        "duplicate_id",
        "invented_answer",
        "invented_evidence",
        "wrong_source",
        "no_support",
    ],
)
def test_invalid_judge_cannot_pass_by_omission_or_fabricated_quotations(failure: str) -> None:
    case = CASES[0]
    sample = case.samples[0]
    sources = load_case_sources(case, ROOT)
    assessment = fixture_assessment(case, sample)
    first = assessment.findings[0]
    if failure == "missing_id":
        assessment.findings.pop()
    elif failure == "duplicate_id":
        assessment.findings.append(first)
    elif failure == "invented_answer":
        first.answer_quote = "An invented answer sentence."
    elif failure == "invented_evidence":
        first.evidence[0].quote = "Invented staff observation."
    elif failure == "wrong_source":
        first.evidence[0].source_id = "unknown"
    elif failure == "no_support":
        first.evidence = []
    result = assessment_report(case, sample, sources, assessment)
    assert result["semantic_status"] == "invalid_evaluation"
    assert result["overall_status"] == "unverified"


def test_final_displayed_answer_is_graded_including_fallback_text() -> None:
    case = CASES[-1]
    original = next(sample for sample in case.samples if sample.id == "label-only")
    sample = original.model_copy(
        update={
            "answer": "The guide requires rotation of small decisions and a decision deadline for shared arrangements."
        }
    )
    payload = json.loads(
        cast(str, assessment_messages(case, sample, load_case_sources(case, ROOT))[-1].content)
    )
    assert payload["answer"] == sample.answer
    assert "explanation" not in payload["citation_sections"][0]
    assert "CONDITIONAL." not in payload["answer"]


def test_empty_answer_cannot_pass_with_only_successful_prohibitions() -> None:
    case = CASES[0]
    sources = load_case_sources(case, ROOT)
    sample = AnswerSample(id="empty", sections=[], expected={a.id: False for a in case.assertions})
    assessment = AnswerAssessment(
        findings=[
            AssertionFinding(
                assertion_id=a.id,
                verdict="missing" if a.kind == "requirement" else "pass",
                reason="No answer was produced.",
                evidence=[],
            )
            for a in case.assertions
        ]
    )
    result = assessment_report(case, sample, sources, assessment)
    assert result["semantic_status"] == "fail" and result["overall_status"] == "fail"


def test_uncertainty_technical_errors_and_false_passes_stay_separate() -> None:
    case = CASES[0]
    sample = case.samples[0]
    assessment = fixture_assessment(case, sample)
    assessment.findings[0].verdict = "uncertain"
    assert (
        assessment_report(case, sample, load_case_sources(case, ROOT), assessment)["overall_status"]
        == "unverified"
    )
    metrics = calibration_metrics(
        [
            ({a.id: False for a in case.assertions}, fixture_assessment(case, sample)),
            (sample.expected, None),
            (sample.expected, assessment),
        ]
    )
    assert metrics["false_passes"] == len(case.assertions)
    assert metrics["technical_errors"] == len(case.assertions)
    assert metrics["abstentions"] == 1
    assert metrics["agreement"] != 1


def test_empty_or_prohibition_only_evaluation_cannot_be_a_completeness_pass() -> None:
    with pytest.raises(ValueError):
        calibration_metrics([])
    data = CASES[0].model_dump(mode="json")
    for assertion in data["assertions"]:
        assertion["kind"] = "prohibition"
    with pytest.raises(ValidationError):
        AssertionCase.model_validate(data)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["flush", "get_many"])
async def test_telemetry_failure_keeps_the_paid_judge_result_archived(
    tmp_path: Path, failure: str
) -> None:
    archive = tmp_path / "calibration.json"
    record = {"assessment": {"findings": [{"assertion_id": "morning", "verdict": "pass"}]}}

    def persist() -> None:
        archive.write_text(json.dumps({"records": [record]}))

    class FailingTelemetry:
        api: Any

        def flush(self) -> None:
            if failure == "flush":
                raise OSError("Langfuse flush unavailable")

    def get_many(**_: Any) -> Any:
        raise OSError("Langfuse observations unavailable")

    client = FailingTelemetry()
    client.api = SimpleNamespace(observations=SimpleNamespace(get_many=get_many))
    await _capture_telemetry(client, "trace-id", record, persist)  # type: ignore[arg-type]

    archived = json.loads(archive.read_text())["records"][0]
    assert archived["assessment"]["findings"][0]["verdict"] == "pass"
    assert archived["telemetry_errors"] == ["OSError"]
    assert "technical_error_type" not in archived
    metrics = calibration_metrics(
        [
            (
                {"morning": True},
                AnswerAssessment(
                    findings=[
                        AssertionFinding(
                            assertion_id="morning",
                            verdict="pass",
                            reason="The checked answer states the observation.",
                            answer_quote="Staff observed daily singing.",
                            evidence=[],
                        )
                    ]
                ),
            )
        ]
    )
    assert metrics["technical_errors"] == 0
    assert metrics["agreement"] == 1


def test_judge_result_is_checkpointed_before_langfuse_context_exit() -> None:
    record = {"assessment": {"findings": [{"assertion_id": "morning", "verdict": "pass"}]}}
    expected = {"morning": True}
    assessment = AnswerAssessment(
        findings=[
            AssertionFinding(
                assertion_id="morning",
                verdict="pass",
                reason="The answer states the observation.",
                answer_quote="Staff observed daily singing.",
                evidence=[],
            )
        ]
    )
    records: list[dict[str, Any]] = []
    measurements: list[tuple[dict[str, bool], AnswerAssessment | None]] = []
    archive: list[dict[str, Any]] = []

    class FailingObservationContext:
        def __enter__(self) -> Any:
            return self

        def __exit__(self, *_: Any) -> None:
            raise OSError("Langfuse context exit failed")

    with pytest.raises(OSError, match="context exit failed"):
        with FailingObservationContext():
            _archive_judge_result(
                record,
                expected,
                assessment,
                records,
                measurements,
                lambda: archive.append({"records": list(records)}),
            )

    assert archive[0]["records"][0]["assessment"] == record["assessment"]
    assert calibration_metrics(measurements)["technical_errors"] == 0
