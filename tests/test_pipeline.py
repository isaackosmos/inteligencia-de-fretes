"""Testes de orquestração com processos simulados, sem executar treinamento."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("run_pipeline", Path(__file__).resolve().parents[1] / "scripts/run_pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class PipelineTests(unittest.TestCase):
    def run_mocked(self, responses=None, **options):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in pipeline.ORIGINALS:
            (root / name).write_text("fixture", encoding="utf-8")
        with patch.object(pipeline.platform, "platform", return_value="mock-platform"), patch.object(pipeline.subprocess, "run", side_effect=responses, return_value=subprocess.CompletedProcess([], 0)) as runner:
            code, path = pipeline.run_pipeline(root, **options)
        return code, json.loads(path.read_text()), runner

    def test_complete_run_uses_current_python_and_records_provenance(self):
        code, report, runner = self.run_mocked()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "success")
        self.assertTrue(report["complete"])
        self.assertTrue(report["sources_unchanged"])
        self.assertEqual(len(report["source_sha256_before"]), 6)
        self.assertEqual(runner.call_count, 8)
        self.assertTrue(all(step["command"][0] == pipeline.sys.executable for step in report["steps"]))
        self.assertTrue(all(step["finished_at_utc"].endswith("+00:00") for step in report["steps"]))

    def test_skip_flags_never_claim_complete(self):
        code, report, runner = self.run_mocked(skip_train=True, skip_tests=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "partial_success")
        self.assertFalse(report["complete"])
        self.assertEqual(runner.call_count, 6)
        self.assertEqual([s["name"] for s in report["steps"] if s["status"] == "skipped"], ["train", "tests"])

    def test_failure_stops_later_stages_and_records_exit_code(self):
        code, report, runner = self.run_mocked(responses=[subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 7)])
        self.assertEqual(code, 7)
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["complete"])
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(report["steps"][-1]["name"], "build_data")
        self.assertEqual(report["steps"][-1]["returncode"], 7)

    def test_launch_error_is_audited(self):
        code, report, runner = self.run_mocked(responses=OSError("cannot launch"))
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(runner.call_count, 1)
        self.assertIn("cannot launch", report["steps"][0]["error"])


if __name__ == "__main__":
    unittest.main()
