"""Offline tests for exact archived-source rehydration."""

import json
from typing import Any

import pytest

from tests.evaluation.support.geval_sources import restore_recorded_sources


def _observation(observation_id: str, text: str) -> dict[str, Any]:
    return {
        "id": observation_id,
        "output": json.dumps([{"source_key": "stone:abc", "text": text}], ensure_ascii=False),
    }


def test_reference_selects_the_observation_revision_for_same_source_key() -> None:
    observations = [
        _observation("revision-old", "Old recorded text"),
        _observation("revision-current", "Current recorded text"),
    ]

    assert (
        restore_recorded_sources(
            {"source_ref": "stone:abc", "observation_id": "revision-current"}, observations
        )
        == "Current recorded text"
    )


def test_missing_observation_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="No archived observation"):
        restore_recorded_sources({"source_ref": "stone:abc", "observation_id": "missing"}, [])


def test_conflicting_text_for_same_observation_and_source_is_rejected() -> None:
    observations = [
        _observation("same-id", "First text"),
        _observation("same-id", "Different text"),
    ]

    with pytest.raises(ValueError, match="Conflicting document text"):
        restore_recorded_sources(
            {"source_ref": "stone:abc", "observation_id": "same-id"}, observations
        )


def test_nested_json_request_is_decoded_and_references_are_restored() -> None:
    request = json.dumps(
        {
            "messages": [
                {"role": "user", "content": {"source_ref": "stone:abc", "observation_id": "obs-1"}}
            ]
        },
        ensure_ascii=False,
    )

    assert restore_recorded_sources(request, [_observation("obs-1", "Recorded text")]) == {
        "messages": [{"role": "user", "content": "Recorded text"}]
    }

    cyclic: list[Any] = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match="Cycle detected"):
        restore_recorded_sources(cyclic, [])
