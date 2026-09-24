"""Prove the delivery regression suite rejects defects in the validator itself."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidatorRedDrills(unittest.TestCase):
    """Reuse the real suite in a disposable source copy without changing its assertions."""

    def test_validator_mutations(self) -> None:
        """Require baseline green, an intended test assertion, byte restoration, and green again."""
        with tempfile.TemporaryDirectory(prefix="delivery-drill-") as temporary:
            workspace = Path(temporary)
            self.assertTrue(
                workspace.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
            )
            for directory in ("scripts", "tests", "templates/workflow"):
                shutil.copytree(
                    ROOT / directory,
                    workspace / directory,
                    ignore=shutil.ignore_patterns("__pycache__", ".mypy_cache", ".ruff_cache"),
                )
            shutil.copyfile(ROOT / "AGENTS.md", workspace / "AGENTS.md")
            cases = (
                (
                    "scripts/delivery/checks.py",
                    " or proof.mutated_exit <= 0",
                    "",
                    "test_surviving_mutation",
                ),
                (
                    "scripts/delivery/checks.py",
                    'if stage not in {"readiness", "closure", "resume"}:',
                    "if False:",
                    "test_unknown_stage",
                ),
            )
            baseline = self.run_suite(workspace)
            self.assertEqual(baseline.returncode, 0, baseline.stdout)
            for relative, before, after, expected_test in cases:
                with self.subTest(defect=expected_test):
                    source = workspace / relative
                    original = source.read_bytes()
                    text = original.decode("utf-8")
                    self.assertEqual(text.count(before), 1, "Mutation anchor drifted")
                    try:
                        source.write_bytes(text.replace(before, after).encode("utf-8"))
                        red = self.run_suite(workspace)
                        self.assertNotEqual(red.returncode, 0, "Validator defect survived")
                        self.assertIn(expected_test, red.stdout)
                        self.assertIn("AssertionError", red.stdout)
                    finally:
                        source.write_bytes(original)
                        self.assertEqual(source.read_bytes(), original)
                    restored = self.run_suite(workspace)
                    self.assertEqual(restored.returncode, 0, restored.stdout)

    @staticmethod
    def run_suite(workspace: Path) -> subprocess.CompletedProcess[str]:
        """Run the unmodified core tests with a fresh interpreter and no cached bytecode."""
        # The interpreter, module, test pattern, and owned cwd are fixed by this
        # harness. No shell or outside command string participates in execution.
        return subprocess.run(  # nosec B603
            [
                sys.executable,
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_verify_delivery.py",
                "-v",
            ],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
