"""Restore traced document references from the exact archived observations.

Workflow captures may replace source documents with references that identify both
an observation and a source key. This helper rehydrates those references from the
captured observation outputs only. It recursively decodes JSON-encoded strings,
rejects missing or conflicting evidence, and detects cyclic Python containers; it
does not evaluate the model response or consult fixtures and backends.
"""

import json
from typing import Any


def _decoded(value: Any) -> Any:
    """Decode JSON-encoded strings while leaving ordinary text unchanged."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _documents(value: Any, active: set[int]) -> list[dict[str, Any]]:
    """Find document-shaped mappings in a recursively decoded observation output."""
    value = _decoded(value)
    if isinstance(value, dict):
        identity = id(value)
        if identity in active:
            raise ValueError("Cycle detected in archived observation output")
        active.add(identity)
        try:
            found = (
                [value]
                if isinstance(value.get("source_key"), str) and isinstance(value.get("text"), str)
                else []
            )
            for child in value.values():
                found.extend(_documents(child, active))
            return found
        finally:
            active.remove(identity)
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active:
            raise ValueError("Cycle detected in archived observation output")
        active.add(identity)
        try:
            return [document for child in value for document in _documents(child, active)]
        finally:
            active.remove(identity)
    return []


def _restore(value: Any, observations: list[dict[str, Any]], active: set[int]) -> Any:
    if isinstance(value, str):
        decoded = _decoded(value)
        if decoded is value:
            return value
        return _restore(decoded, observations, active)

    if isinstance(value, dict):
        identity = id(value)
        if identity in active:
            raise ValueError("Cycle detected while restoring traced source references")
        if len(value) == 2 and set(value) == {"source_ref", "observation_id"}:
            source_key = value["source_ref"]
            observation_id = value["observation_id"]
            if not isinstance(source_key, str) or not isinstance(observation_id, str):
                raise ValueError("Traced source reference must contain string identifiers")
            matched = [item for item in observations if item.get("id") == observation_id]
            if not matched:
                raise ValueError(f"No archived observation matches id {observation_id!r}")
            texts = {
                document["text"]
                for item in matched
                for document in _documents(item.get("output"), set())
                if document["source_key"] == source_key
            }
            if not texts:
                raise ValueError(
                    f"No document for source key {source_key!r} in observation {observation_id!r}"
                )
            if len(texts) != 1:
                raise ValueError(
                    f"Conflicting document text for source key {source_key!r} "
                    f"in observation {observation_id!r}"
                )
            return next(iter(texts))
        active.add(identity)
        try:
            return {key: _restore(child, observations, active) for key, child in value.items()}
        finally:
            active.remove(identity)

    if isinstance(value, list):
        identity = id(value)
        if identity in active:
            raise ValueError("Cycle detected while restoring traced source references")
        active.add(identity)
        try:
            return [_restore(child, observations, active) for child in value]
        finally:
            active.remove(identity)

    if isinstance(value, tuple):
        identity = id(value)
        if identity in active:
            raise ValueError("Cycle detected while restoring traced source references")
        active.add(identity)
        try:
            return tuple(_restore(child, observations, active) for child in value)
        finally:
            active.remove(identity)
    return value


def restore_recorded_sources(value: Any, observations: list[dict[str, Any]]) -> Any:
    """Replace traced source placeholders using only the matching archived evidence."""
    return _restore(value, observations, set())
