"""Identifiers shared by local evaluation runners and Langfuse traces."""

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime

COMPARISON_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,110}$")


@dataclass(frozen=True)
class EvaluationRunIdentity:
    comparison_id: str
    run_number: int
    run_id: str
    session_id: str

    @classmethod
    def create(cls, comparison_id: str, run_number: int) -> "EvaluationRunIdentity":
        if not COMPARISON_ID_PATTERN.fullmatch(comparison_id):
            raise ValueError("Comparison ID must use 1-110 letters, digits, dots, _ or -")
        if run_number < 1:
            raise ValueError("Run number must be a positive integer")
        run_id = f"STPY-{comparison_id}-r{run_number:02d}"
        if len(run_id) > 128:
            raise ValueError("Derived Langfuse session ID exceeds 128 characters")
        return cls(comparison_id, run_number, run_id, run_id)

    def as_metadata(self) -> dict[str, str | int]:
        return {
            "comparison_id": self.comparison_id,
            "run_number": self.run_number,
            "run_id": self.run_id,
        }


def comparison_id_from_environment(started_at: datetime) -> str:
    comparison_id = os.getenv("EVALUATION_COMPARISON_ID")
    if comparison_id is None:
        comparison_id = f"cmp-{started_at.astimezone(UTC):%Y%m%dT%H%M%S%fZ}"
    if not COMPARISON_ID_PATTERN.fullmatch(comparison_id):
        raise ValueError("EVALUATION_COMPARISON_ID must use 1-110 letters, digits, dots, _ or -")
    return comparison_id


def first_run_number_from_environment() -> int:
    value = os.getenv("EVALUATION_RUN_NUMBER", "1")
    try:
        run_number = int(value)
    except ValueError as error:
        raise ValueError("EVALUATION_RUN_NUMBER must be a positive integer") from error
    if run_number < 1:
        raise ValueError("EVALUATION_RUN_NUMBER must be a positive integer")
    return run_number
