"""Grounding dataset separation and metric accounting, not verifier model quality."""

import json
from pathlib import Path

import pytest

from tests.evaluation.support.grounding_cases import grounding_metrics

ROOT = Path(__file__).resolve().parents[3]
HOLDOUT = json.loads((ROOT / "fixtures/agent-eval/grounding-en/holdout.json").read_text())
CATALOG = json.loads((ROOT / "fixtures/knowledge/grounding/grounding_en-v1.json").read_text())


def test_holdout_does_not_reuse_catalog_example_wording() -> None:
    examples = {entry["text"] for entry in CATALOG if entry["entry_kind"] == "example"}
    assert not examples.intersection(case["question"] for case in HOLDOUT)


def test_metrics_do_not_count_technical_failures_as_correct_rejections() -> None:
    metrics = grounding_metrics(
        ["supported", "unknown", "contradicted"], ["supported", None, "supported"]
    )
    assert metrics["technical_failures"] == 1
    assert metrics["false_acceptances"] == 1
    assert metrics["classification_accuracy"] == pytest.approx(1 / 3)
    assert metrics["acceptance_accuracy"] == pytest.approx(1 / 3)
    assert metrics["supported_precision"] == 0.5
