import json
import tempfile
import unittest
from pathlib import Path

from program_ops.core import InputError, generate_artifacts, load_program, validate_program


ROOT = Path(__file__).resolve().parents[1]


class ProgramOpsTests(unittest.TestCase):
    def test_sample_generates_complete_artifact_set(self):
        data = load_program(ROOT / "examples" / "launch-input.json")
        with tempfile.TemporaryDirectory() as directory:
            result = generate_artifacts(data, Path(directory))
            names = {path.name for path in result.files}
            self.assertEqual(
                names,
                {"roadmap.md", "dependencies.mmd", "raid-log.md", "executive-brief.md", "run-metrics.json", "trace.jsonl"},
            )
            self.assertEqual(result.metrics["workstreams"], 4)
            self.assertEqual(result.metrics["dependencies"], 5)
            self.assertTrue(result.metrics["human_review"])
            self.assertIn("HUMAN REVIEW REQUIRED", (Path(directory) / "roadmap.md").read_text())

    def test_approve_flag_changes_review_gate(self):
        data = load_program(ROOT / "examples" / "launch-input.json")
        with tempfile.TemporaryDirectory() as directory:
            generate_artifacts(data, Path(directory), approved=True)
            self.assertIn("APPROVED FOR PLANNING", (Path(directory) / "executive-brief.md").read_text())

    def test_unknown_dependency_is_rejected(self):
        data = json.loads((ROOT / "examples" / "launch-input.json").read_text())
        data["workstreams"][0]["depends_on"] = ["MISSING"]
        with self.assertRaisesRegex(InputError, "unknown dependencies"):
            validate_program(data)

    def test_dependency_cycle_is_rejected(self):
        data = json.loads((ROOT / "examples" / "launch-input.json").read_text())
        data["workstreams"][0]["depends_on"] = ["WS4"]
        with self.assertRaisesRegex(InputError, "Dependency cycle"):
            validate_program(data)

    def test_missing_required_field_is_rejected(self):
        data = json.loads((ROOT / "examples" / "launch-input.json").read_text())
        del data["objective"]
        with self.assertRaisesRegex(InputError, "Missing required field"):
            validate_program(data)


if __name__ == "__main__":
    unittest.main()
