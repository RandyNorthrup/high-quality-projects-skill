"""Verify the formatting helper's exit contract through its documented command line."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import override

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-format-safe.py"
EXIT_IDENTICAL = 0
EXIT_CHANGED = 1
EXIT_UNREADABLE = 2


class FormatSafetyTests(unittest.TestCase):
    """Distinguish identical syntax, changed syntax, and inputs that cannot be compared."""

    @override
    def setUp(self) -> None:
        """Create disposable source files for each comparison."""
        self.temporary = tempfile.TemporaryDirectory(prefix="format-safety-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name: str, content: bytes) -> Path:
        """Store exact source bytes, including non-UTF-8 encodings."""
        path = self.root / name
        path.write_bytes(content)
        return path

    def compare(self, *arguments: Path | str) -> subprocess.CompletedProcess[str]:
        """Run the helper exactly as the retrofit workflow documents it."""
        # Trusted interpreter and checked-in helper; no shell.
        return subprocess.run(  # noqa: S603  # nosec B603
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def test_layout_only_change_is_identical(self) -> None:
        """Quote, spacing, and trailing-comma changes leave the parsed syntax unchanged."""
        before = self.write("before.py", b"values = [ 'a','b' ]\n")
        after = self.write("after.py", b'values = [\n    "a",\n    "b",\n]\n')
        result = self.compare(before, after)
        self.assertEqual(result.returncode, EXIT_IDENTICAL, result.stderr)
        self.assertIn("AST identical", result.stdout)

    def test_structural_change_is_reported(self) -> None:
        """A changed operand is a syntax change, not formatting."""
        before = self.write("before.py", b"limit = 10\n")
        after = self.write("after.py", b"limit = 11\n")
        result = self.compare(before, after)
        self.assertEqual(result.returncode, EXIT_CHANGED, result.stderr)
        self.assertIn("AST DIFFERS", result.stdout)

    def test_declared_source_encoding_is_honored(self) -> None:
        """A valid PEP 263 Latin-1 file compares equal to its UTF-8 reformatting."""
        before = self.write("before.py", b"# -*- coding: latin-1 -*-\nname = '\xe9'\n")
        after = self.write("after.py", 'name = "é"\n'.encode())
        result = self.compare(before, after)
        self.assertEqual(result.returncode, EXIT_IDENTICAL, result.stderr)

    def test_inputs_that_cannot_be_compared_are_not_changes(self) -> None:
        """Missing, undecodable, and invalid sources use the input-error exit, not 'changed'."""
        valid = self.write("valid.py", b"answer = 42\n")
        cases = {
            "missing file": self.root / "missing.py",
            "undeclared non-UTF-8 bytes": self.write("latin.py", b"name = '\xe9'\n"),
            "syntax error": self.write("broken.py", b"def broken(:\n"),
            "directory": self.root,
        }
        for label, path in cases.items():
            with self.subTest(label):
                result = self.compare(valid, path)
                self.assertEqual(result.returncode, EXIT_UNREADABLE, result.stdout + result.stderr)
                self.assertIn("ERROR", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_wrong_argument_count_prints_usage(self) -> None:
        """The command refuses to guess which files to compare."""
        result = self.compare(self.write("only.py", b"pass\n"))
        self.assertEqual(result.returncode, EXIT_UNREADABLE)
        self.assertIn("verify-format-safe.py BEFORE.py AFTER.py", result.stderr)


if __name__ == "__main__":
    unittest.main()
