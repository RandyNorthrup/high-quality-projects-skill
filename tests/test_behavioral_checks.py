"""Prove independent trial oracles reject planted false-green outcomes."""

import tempfile
import unittest
from pathlib import Path

from tests.behavioral.check import check_case, check_product
from tests.behavioral.prepare import BAD_ORDER, GOOD_ORDER, REAL_TEST, VACUOUS_TEST, make_case


class OutcomeOracleTests(unittest.TestCase):
    """Exercise the actual evaluator against broken code and misleading reports."""

    def setUp(self) -> None:
        """Build a disposable trial with a realistic committed baseline."""
        self.temporary = tempfile.TemporaryDirectory(prefix="hqp-oracle-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "trial"

    def test_correct_behavior_and_sensitive_tests(self) -> None:
        """Accept correct code, then reject broken code and a vacuous suite independently."""
        make_case(self.root, "reuse")
        source = self.root / "src/orders.py"
        test = self.root / "tests/test_orders.py"
        source.write_text(GOOD_ORDER, encoding="utf-8")
        test.write_text(REAL_TEST, encoding="utf-8")
        self.assertEqual(check_product(self.root, "reuse"), [])
        source.write_text(BAD_ORDER, encoding="utf-8")
        self.assertTrue(check_product(self.root, "reuse"))
        source.write_text(GOOD_ORDER, encoding="utf-8")
        test.write_text(VACUOUS_TEST, encoding="utf-8")
        self.assertTrue(check_product(self.root, "reuse"))
        test.unlink()
        self.assertTrue(check_product(self.root, "reuse"))

    def test_duplicate_implementation_rejected(self) -> None:
        """Correct outputs cannot hide a second implementation of canonical domain logic."""
        make_case(self.root, "reuse")
        duplicated = GOOD_ORDER.replace("from src.quantity import quantity", "").replace(
            'return {"quantity": quantity(value)}',
            'if value < 0:\n        raise ValueError("negative")\n    return {"quantity": value}',
        )
        (self.root / "src/orders.py").write_text(duplicated, encoding="utf-8")
        self.assertIn("canonical", " ".join(check_product(self.root, "reuse")))

    def test_conflict_and_discovery_scope(self) -> None:
        """A claimed success cannot excuse premature product changes."""
        make_case(self.root, "conflict")
        (self.root / "agent-response.md").write_text("All done!", encoding="utf-8")
        self.assertTrue(check_case(self.root, "conflict")["mechanical_pass"])
        (self.root / "src/orders.py").write_text(GOOD_ORDER, encoding="utf-8")
        self.assertFalse(check_case(self.root, "conflict")["mechanical_pass"])
        self.assertFalse(check_case(self.root, "discovery")["mechanical_pass"])

    def test_external_outcome_cannot_be_replayed(self) -> None:
        """Replayed side effects fail regardless of an agent's success statement."""
        make_case(self.root, "outcome")
        (self.root / "agent-response.md").write_text("All done!", encoding="utf-8")
        result = check_case(self.root, "outcome")
        self.assertFalse(result["mechanical_pass"])
        (self.root / "deployment-replayed.txt").write_text("replayed", encoding="utf-8")
        self.assertIn(
            "Completed deployment was replayed.", check_case(self.root, "outcome")["findings"]
        )


if __name__ == "__main__":
    unittest.main()
