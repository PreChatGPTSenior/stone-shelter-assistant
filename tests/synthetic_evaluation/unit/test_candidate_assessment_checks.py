"""Checks of the fixed assessment evaluator and its input fixture, not model quality."""

import json
from pathlib import Path

from stone_shelter_assistant.assistant.candidate_evidence import CandidateEvidence
from tests.evaluation.support.candidate_assessment import check_assessment

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures/assistant/quiet-home-assessment.json"


def test_live_assessment_check_rejects_unrecognized_criterion_id_without_model_call() -> None:
    snapshot = json.loads(FIXTURE.read_text())
    assessment = CandidateEvidence.model_validate(
        {
            "character": [
                {
                    "stone_id": card["id"],
                    "criterion_id": "fabricated.character.1",
                    "fragment_id": 1,
                    "source_ref": "biography",
                    "finding": "confirmed",
                    "quote": card["biography"],
                }
                for card in snapshot["cards"]
            ],
            "individual_compatibility": [],
        }
    )
    checks = check_assessment(assessment, snapshot)
    assert checks["evidence_grounded"] is False
    assert checks["character_coverage"] is False


def test_active_replay_fixture_uses_current_schema_and_explicit_sources() -> None:
    snapshot = json.loads(FIXTURE.read_text())
    assert snapshot["schema"] == CandidateEvidence.model_json_schema()
    sources = json.loads(snapshot["messages"][1]["content"])["candidate_sources"]
    assert isinstance(sources, list)
    assert all(set(source) == {"stone_id", "source_ref", "text"} for source in sources)
