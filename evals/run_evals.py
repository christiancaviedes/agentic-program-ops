"""Small deterministic launch gate for portfolio and CI evidence."""

import json
import tempfile
from pathlib import Path

from program_ops.core import generate_artifacts, load_program


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    data = load_program(ROOT / "examples" / "launch-input.json")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        result = generate_artifacts(data, output)
        checks = {
            "artifact_completeness": len(result.files) == 6,
            "dependency_recall": result.metrics["dependencies"] == 5,
            "risk_visibility": "Evaluation coverage" in (output / "raid-log.md").read_text(),
            "human_gate_present": "HUMAN REVIEW REQUIRED" in (output / "executive-brief.md").read_text(),
            "zero_model_cost": result.metrics["estimated_model_cost_usd"] == 0,
        }
    report = {"passed": sum(checks.values()), "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
