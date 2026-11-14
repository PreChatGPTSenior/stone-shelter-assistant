"""Missing required evidence must not yield a passing saved-run evaluation."""

from typing import Any

import pytest

from tests.evaluation.support.scenario_stages import failed_evaluation_checks
from tests.evaluation.test_saved_run_evaluation import _evaluate_saved_result


@pytest.mark.parametrize(
    ("expected", "targets", "failed_check"),
    [
        (
            {"pair": {"key": "GRANITE+GRANITE", "verdict": "CONDITIONAL"}},
            {},
            "Q01.structured_expectations",
        ),
        (
            {"condition_checks": {"pair_key": "GRANITE+GRANITE", "rotate_decisions": "confirmed"}},
            {},
            "Q01.structured_expectations",
        ),
        (
            {},
            {"expected_dispositions": {"missing-stone": "recommended"}},
            "Q01.recommendations.disposition_check",
        ),
    ],
    ids=["missing-pair", "missing-condition", "missing-candidate-decision"],
)
def test_saved_run_rejects_missing_required_measurements(
    expected: dict[str, Any], targets: dict[str, Any], failed_check: str
) -> None:
    record = {
        "case_id": "Q01",
        "status": "completed",
        "expected": expected,
        "graph_state": {
            "plan_status": "accepted",
            "criteria_status": "parsed",
            "selection_status": "selected",
            "question_coverage_status": "complete",
            "recommended_stone_ids": [],
            "result": {"answer": "No candidate assessment was recorded.", "sources": {}},
        },
    }
    report = _evaluate_saved_result(
        record,
        {
            "suite_id": "missing-evidence-check",
            "scenarios": {"Q01": {"stage_applicability": "not_applicable", **targets}},
        },
    )
    assert report["scenario_reports"][0]["workflow_integrity"]["status"] == "pass"
    assert failed_check in failed_evaluation_checks(report)
