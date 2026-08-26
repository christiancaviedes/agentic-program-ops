import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DemoTests(unittest.TestCase):
    def test_demo_exposes_real_compiler_controls(self):
        html = (ROOT / "prototype" / "index.html").read_text(encoding="utf-8")
        for element_id in (
            "programInput",
            "fileInput",
            "approvalToggle",
            "compileButton",
            "artifactTabs",
            "downloadButton",
        ):
            self.assertIn(f'id="{element_id}"', html)

    def test_demo_compiles_and_downloads_all_artifacts(self):
        javascript = (ROOT / "prototype" / "app.js").read_text(encoding="utf-8")
        for artifact in (
            "roadmap.md",
            "dependencies.mmd",
            "raid-log.md",
            "executive-brief.md",
            "run-metrics.json",
            "trace.jsonl",
        ):
            self.assertIn(artifact, javascript)
        self.assertIn("buildZip(generated)", javascript)
        self.assertIn("rejectCycles(graph)", javascript)


if __name__ == "__main__":
    unittest.main()
