"""Local evaluation artifacts and bounded Langfuse observation export.

Reserves a new run directory, atomically writes JSON, and checkpoints model
results before optional telemetry reads. Failures fetching telemetry remain
separate from the model assessment. No workflow or model is executed here.
"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langfuse import Langfuse


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def reserve_run_directory(root: Path, run_id: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    folder = root / run_id
    folder.mkdir(exist_ok=False)
    return folder


async def capture_telemetry(
    client: Langfuse,
    trace_id: str,
    record: dict[str, Any],
    persist: Callable[[], None],
) -> None:
    """Archive the judge result first; telemetry failure must not erase semantic grading."""
    persist()
    observations = []
    try:
        await asyncio.to_thread(client.flush)
        for _ in range(8):
            observations = (
                await asyncio.to_thread(
                    client.api.observations.get_many,
                    trace_id=trace_id,
                    fields="basic,io,model,usage",
                    limit=100,
                )
            ).data
            if any(o.type == "GENERATION" and o.output for o in observations):
                break
            await asyncio.sleep(2)
        record["observations"] = [o.model_dump(mode="json") for o in observations]
    except Exception as error:
        record.setdefault("telemetry_errors", []).append(type(error).__name__)
        record["observations"] = [o.model_dump(mode="json") for o in observations]
    persist()
