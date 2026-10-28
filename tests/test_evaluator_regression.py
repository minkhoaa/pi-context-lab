"""tests/test_evaluator_regression.py

Automated offline tests verifying the Task L independent evaluator against:
1. The original broken Task L fixture — expected FAIL.
2. A verified correct implementation — expected PASS.
3. A deliberately incorrect implementation — expected FAIL.
4. A workspace with modified public tests — expected rejection.
"""

import sys
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluators.eval_task_l import evaluate_task_l


class TestEvaluatorRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = ROOT / "fixtures" / "task-l"
        cls.pilot01_dir = ROOT / "workspaces" / "pilot-01_A_task-l_r1"

    def test_01_original_broken_fixture_fails(self):
        """Case 1: The original broken Task L fixture must FAIL with score 0.0."""
        result = evaluate_task_l(str(self.fixture_dir))
        self.assertFalse(result["passed"], "Original broken fixture unexpectedly passed.")
        self.assertEqual(result["score"], 0.0, f"Expected score 0.0, got {result['score']}")
        self.assertFalse(result["independent_tests_passed"])
        self.assertTrue(result["workspace_tests_immutable"])

    def test_02_verified_correct_implementation_passes(self):
        """Case 2: A verified correct solution must PASS with score 1.0."""
        self.assertTrue(self.pilot01_dir.is_dir(), "pilot-01 workspace missing.")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "task-l"
            shutil.copytree(self.pilot01_dir, target)
            result = evaluate_task_l(str(target))
            self.assertTrue(result["passed"], f"Verified correct solution failed: {result['details']}")
            self.assertEqual(result["score"], 1.0)
            self.assertTrue(result["independent_tests_passed"])
            self.assertTrue(result["workspace_tests_immutable"])

    def test_03_deliberately_incorrect_implementation_fails(self):
        """Case 3: A deliberately broken buffer or aggregator must FAIL."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "task-l"
            shutil.copytree(self.pilot01_dir, target)
            # Break aggregator to reintroduce sequence mismatch
            aggregator_file = target / "pipeline_engine" / "aggregator.py"
            aggregator_file.write_text(
                "class StreamAggregator:\n"
                "    def __init__(self, metrics=None): self.collected_items = []\n"
                "    def ingest(self, chunk): raise RuntimeError('Broken ingest')\n"
                "    def total_items(self): return len(self.collected_items)\n",
                encoding="utf-8"
            )
            result = evaluate_task_l(str(target))
            self.assertFalse(result["passed"])
            self.assertLess(result["score"], 1.0)
            self.assertFalse(result["independent_tests_passed"])

    def test_04_tampered_workspace_tests_rejected(self):
        """Case 4: A workspace with tampered test files must be rejected even if its tests pass."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "task-l"
            shutil.copytree(self.pilot01_dir, target)
            test_file = target / "tests" / "test_pipeline.py"
            test_file.write_text("# Tampered test file\nimport unittest\n", encoding="utf-8")
            result = evaluate_task_l(str(target))
            self.assertFalse(result["passed"], "Tampered workspace tests were not rejected.")
            self.assertFalse(result["workspace_tests_immutable"])
            self.assertIn("tests/test_pipeline.py", result["details"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
