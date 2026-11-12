"""Generate a pure, offline stage report from a frozen challenge-run archive."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tests.evaluation.scenario_stages import evaluate_run

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TARGETS = (
    ROOT / "tests/fixtures/agent-eval/questions-challenge-20/scenario-evaluation-targets.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_archive", type=Path, help="JSON produced by the opt-in live runner")
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run: dict[str, Any] = json.loads(args.run_archive.read_text())
    targets: dict[str, Any] = json.loads(args.targets.read_text())
    report = evaluate_run(run, targets)
    report["source_archive"] = str(args.run_archive)
    report["source_archive_sha256"] = hashlib.sha256(args.run_archive.read_bytes()).hexdigest()
    report["target_config"] = str(args.targets)
    report["target_config_sha256"] = hashlib.sha256(args.targets.read_bytes()).hexdigest()
    evaluator_path = ROOT / "tests/evaluation/scenario_stages.py"
    report["evaluator_sha256"] = hashlib.sha256(evaluator_path.read_bytes()).hexdigest()
    output = args.output or args.run_archive.with_name(f"{args.run_archive.stem}-evaluation.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
