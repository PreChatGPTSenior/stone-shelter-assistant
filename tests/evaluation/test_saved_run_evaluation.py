"""Re-evaluate saved workflow results without containers, models or Langfuse access.

Set SAVED_RUN_PATH to a full-run result.json or a challenge-run archive. Optional
SAVED_RUN_TARGETS selects reviewed targets. Each execution writes a new timestamped
report beside the input before asserting deterministic checks. Semantic grading
remains unmeasured. Without an explicit input this test is skipped.
"""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.evaluation.support.scenario_stages import (
    evaluate_run,
    evaluate_scenario_record,
    failed_evaluation_checks,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = (
    ROOT / "fixtures/agent-eval/questions-challenge-20/scenario-evaluation-targets.json"
)


def _evaluate_saved_result(saved: dict[str, Any], targets: dict[str, Any]) -> dict[str, Any]:
    if "records" in saved and "selected_case_ids" in saved:
        return evaluate_run(saved, targets)
    if "case_id" in saved and "graph_state" in saved:
        case_id = saved["case_id"]
        if case_id not in targets["scenarios"]:
            raise ValueError(f"No reviewed targets for case {case_id}")
        return {
            "suite_id": targets["suite_id"],
            "source_run_status": saved.get("status"),
            "semantic_judge": "unmeasured",
            "scenario_reports": [evaluate_scenario_record(saved, targets["scenarios"][case_id])],
        }
    raise ValueError("Expected a full-run result.json or a challenge-run archive")


@pytest.mark.skipif(
    not os.getenv("SAVED_RUN_PATH"),
    reason="Select a saved result explicitly with SAVED_RUN_PATH",
)
def test_saved_run_evaluation() -> None:
    source = Path(os.environ["SAVED_RUN_PATH"]).resolve()
    targets_path = Path(os.getenv("SAVED_RUN_TARGETS", str(DEFAULT_TARGETS))).resolve()
    source_bytes = source.read_bytes()
    target_bytes = targets_path.read_bytes()
    report = _evaluate_saved_result(json.loads(source_bytes), json.loads(target_bytes))
    evaluator = ROOT / "tests/evaluation/support/scenario_stages.py"
    report.update(
        source_archive=str(source),
        source_archive_sha256=hashlib.sha256(source_bytes).hexdigest(),
        target_config=str(targets_path),
        target_config_sha256=hashlib.sha256(target_bytes).hexdigest(),
        evaluator_sha256=hashlib.sha256(evaluator.read_bytes()).hexdigest(),
        test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        evaluated_at=datetime.now(UTC).isoformat(),
    )
    failures = failed_evaluation_checks(report)
    report["failed_checks"] = failures
    output = source.with_name(f"{source.stem}-evaluation-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.json")
    with output.open("x") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Saved offline evaluation: {output}")
    assert not failures, f"Deterministic checks failed: {failures}; report: {output}"
