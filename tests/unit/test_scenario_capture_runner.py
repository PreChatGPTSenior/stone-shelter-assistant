import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from tests.integration.test_questions_challenge_20_live import (
    MANIFEST,
    _json_value,
    _persist,
    _selected_cases,
)


def test_selected_cases_defaults_to_manifest_scenarios(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVALUATION_CASE_IDS", raising=False)
    manifest = json.loads(MANIFEST.read_text())
    selected = _selected_cases(manifest)
    assert len(selected) == 20
    assert selected[0]["id"] == "Q01"


def test_selected_cases_preserves_requested_order_and_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = json.loads(MANIFEST.read_text())
    monkeypatch.setenv("EVALUATION_CASE_IDS", "Q03,Q01")
    assert [case["id"] for case in _selected_cases(manifest)] == ["Q03", "Q01"]
    monkeypatch.setenv("EVALUATION_CASE_IDS", "Q99")
    with pytest.raises(ValueError, match="Unknown challenge case IDs"):
        _selected_cases(manifest)


def test_json_value_preserves_nested_dataclass_fields_and_sets() -> None:
    @dataclass
    class Citation:
        source_id: str

    @dataclass
    class Reference:
        citations: list[Citation]
        exact_pair_source_ids: set[str]

    serialized = _json_value(Reference([Citation("pair:granite+obsidian")], {"b", "a"}))
    assert serialized == {
        "citations": [{"source_id": "pair:granite+obsidian"}],
        "exact_pair_source_ids": ["a", "b"],
    }


def test_persist_writes_replaceable_json_archive(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    _persist(path, {"status": "running", "records": [{"case_id": "Q01"}]})
    assert json.loads(path.read_text()) == {"status": "running", "records": [{"case_id": "Q01"}]}
    assert not path.with_suffix(".json.tmp").exists()
