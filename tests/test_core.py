import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from program_ops.core import InputError, generate_artifacts, load_program, validate_program
from program_ops.jira import fetch_jira_issues, jira_issues_to_program
from program_ops.enrichment import enrich_program


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
            trace = json.loads((Path(directory) / "trace.jsonl").read_text())
            self.assertEqual(trace["schema"], "opentelemetry-span-v1")
            self.assertEqual(len(trace["trace_id"]), 32)
            self.assertEqual(trace["resource"]["service.name"], "agentic-program-ops")

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

    def test_jira_adapter_maps_blocks_links_and_owners(self):
        payload = {"issues": [
            {"key": "AI-1", "fields": {"summary": "Policy contract", "assignee": {"displayName": "Maya"}, "project": {"name": "AI Platform"}, "status": {"name": "Done"}, "duedate": "2026-09-10", "issuelinks": [], "labels": ["policy"]}},
            {"key": "AI-2", "fields": {"summary": "Retrieval platform", "assignee": None, "project": {"name": "AI Platform"}, "status": {"name": "In Progress"}, "duedate": None, "issuelinks": [{"type": {"name": "Blocks"}, "inwardIssue": {"key": "AI-1"}}], "labels": []}},
        ]}
        program = jira_issues_to_program(payload, {
            "program": "AI launch", "objective": "Ship safely", "target_date": "2026-11-20", "jira_base_url": "https://example.atlassian.net", "jql": "project=AI"
        })
        self.assertEqual(program["workstreams"][1]["depends_on"], ["AI-1"])
        self.assertEqual(program["workstreams"][1]["owner"], "Unassigned")
        self.assertEqual(program["source"]["type"], "jira-cloud")

    def test_jira_fetch_requires_https(self):
        with self.assertRaisesRegex(InputError, "https"):
            fetch_jira_issues("http://example.test", "owner@example.test", "token", "project=AI")

    def test_enrichment_is_bounded_and_review_only(self):
        class FakeProvider:
            identity = {"adapter": "fake", "model": "test"}

            def complete(self, system, user):
                self.system = system
                self.user = user
                return json.dumps({
                    "executive_narrative": "Validate the pilot boundary.",
                    "questions": ["Who accepts the residual risk?"],
                    "risk_notes": ["Evaluation coverage is an assumption."],
                })

        data = load_program(ROOT / "examples" / "launch-input.json")
        provider = FakeProvider()
        result = enrich_program(data, provider)
        self.assertIn("HUMAN REVIEW REQUIRED", result["status"])
        self.assertFalse(result["guardrails"]["source_mutated"])
        self.assertFalse(result["guardrails"]["approval_inferred"])
        self.assertIn("Do not change", provider.system)


if __name__ == "__main__":
    unittest.main()
