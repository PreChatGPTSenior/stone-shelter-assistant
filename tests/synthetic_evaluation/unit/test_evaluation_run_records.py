"""Configuration and artifact guards prevent accidental duplicate paid executions."""

import json
from pathlib import Path

import pytest

from tests.evaluation.support.model_configurations import model_configurations
from tests.evaluation.support.run_records import reserve_run_directory, write_json


def test_model_configurations_reject_duplicate_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVALUATION_MODEL_CONFIGURATIONS", '[{"name":"same"},{"name":"same"}]')
    with pytest.raises(ValueError, match="unique"):
        model_configurations()


def test_run_directory_reuse_preserves_existing_results(tmp_path: Path) -> None:
    folder = reserve_run_directory(tmp_path, "STPY-comparison-r01")
    result = folder / "result.json"
    write_json(result, {"status": "assessment_failed", "trace_id": "recorded-trace"})
    with pytest.raises(FileExistsError):
        reserve_run_directory(tmp_path, "STPY-comparison-r01")
    assert json.loads(result.read_text()) == {
        "status": "assessment_failed",
        "trace_id": "recorded-trace",
    }
