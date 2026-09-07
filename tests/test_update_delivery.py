"""Verify atomic state changes, conflict refusal, and preservation of user edits."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.delivery.reader import PlanError
from scripts.delivery.writer import UpdateConflictError, acquire_lock, run, update
from tests.delivery_fixtures import plan_text, ready, save


class UpdateTests(unittest.TestCase):
    """Inspect real file outcomes for positive, conflicting, and interrupted updates."""

    def setUp(self) -> None:
        """Create an owned workspace and a valid initial candidate."""
        self.temporary = tempfile.TemporaryDirectory(prefix="delivery-update-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = ready(self.root)
        self.candidate = self.root / "candidate.md"
        self.candidate.write_text(plan_text(self.data), encoding="utf-8")

    def test_create_and_idempotence(self) -> None:
        """Creation writes complete bytes; an identical candidate preserves modification time."""
        result = update(self.root, "PLAN.md", self.candidate, "missing")
        plan = self.root / "PLAN.md"
        self.assertTrue(result.changed)
        self.assertEqual(plan.read_bytes(), self.candidate.read_bytes())
        modified = plan.stat().st_mtime_ns
        repeated = update(self.root, "PLAN.md", self.candidate, result.sha256)
        self.assertFalse(repeated.changed)
        self.assertEqual(plan.stat().st_mtime_ns, modified)
        self.assertFalse((self.root / "PLAN.md.lock").exists())

    def test_preserve_later_user_changes(self) -> None:
        """An outdated precondition cannot overwrite intervening edits."""
        result = update(self.root, "PLAN.md", self.candidate, "missing")
        plan = self.root / "PLAN.md"
        plan.write_bytes(plan.read_bytes() + b"\nUser-owned notes.\n")
        changed = plan.read_bytes()
        with self.assertRaises(UpdateConflictError):
            update(self.root, "PLAN.md", self.candidate, result.sha256)
        self.assertEqual(plan.read_bytes(), changed)

    def test_existing_lock_is_not_deleted(self) -> None:
        """A second writer refuses ownership instead of removing another writer's lock."""
        lock = self.root / "PLAN.md.lock"
        lock.mkdir()
        owner = lock / "owner.json"
        owner.write_text('{"pid": 42}', encoding="utf-8")
        with self.assertRaises(UpdateConflictError):
            update(self.root, "PLAN.md", self.candidate, "missing")
        self.assertEqual(owner.read_text(encoding="utf-8"), '{"pid": 42}')
        self.assertFalse((self.root / "PLAN.md").exists())

    def test_failure_before_replace_preserves_complete_plan(self) -> None:
        """A failed atomic replacement leaves the original bytes and releases our lock."""
        plan = save(self.root, self.data)
        original = plan.read_bytes()
        self.candidate.write_bytes(original + b"\nRevised rationale.\n")
        with (
            patch("scripts.delivery.writer.Path.replace", side_effect=OSError("disk failure")),
            self.assertRaisesRegex(OSError, "disk failure"),
        ):
            update(self.root, "PLAN.md", self.candidate, hashlib.sha256(original).hexdigest())
        self.assertEqual(plan.read_bytes(), original)
        self.assertFalse((self.root / "PLAN.md.lock").exists())
        self.assertEqual(list(self.root.glob(".PLAN.md.*.tmp")), [])

    def test_invalid_candidate_does_not_write(self) -> None:
        """Malformed candidate state cannot replace a valid record."""
        plan = save(self.root, self.data)
        original = plan.read_bytes()
        self.candidate.write_text("# No ledger\n", encoding="utf-8")
        with self.assertRaises(PlanError):
            update(self.root, "PLAN.md", self.candidate, hashlib.sha256(original).hexdigest())
        self.assertEqual(plan.read_bytes(), original)
        self.assertFalse((self.root / "PLAN.md.lock").exists())

    def test_target_escape_is_refused(self) -> None:
        """The writer never accepts a target outside its explicit root."""
        with self.assertRaises(PlanError):
            update(self.root, "../outside.md", self.candidate, "missing")

    def test_partial_lock_write_releases_owned_lock(self) -> None:
        """A partial owner-file write cannot leave our failed acquisition locked."""
        lock = self.root / "PLAN.md.lock"

        def partial_write(path: Path, *_args: object, **_kwargs: object) -> None:
            path.write_bytes(b"partial")
            message = "owner write interrupted"
            raise OSError(message)

        with (
            patch.object(Path, "write_text", partial_write),
            self.assertRaisesRegex(OSError, "owner write interrupted"),
        ):
            acquire_lock(lock, "missing")
        self.assertFalse(lock.exists())

    def test_cli_relative_candidate_and_conflict_exit(self) -> None:
        """The documented CLI resolves candidate paths against the explicit project root."""
        arguments = [
            "--root",
            str(self.root),
            "--plan",
            "PLAN.md",
            "--candidate",
            "candidate.md",
            "--expected-sha256",
            "missing",
        ]
        code, output = run(arguments)
        self.assertEqual(code, 0, output)
        self.assertEqual((self.root / "PLAN.md").read_bytes(), self.candidate.read_bytes())
        code, output = run(arguments)
        self.assertEqual(code, 1, output)
        self.assertIn("update-conflict", output)


if __name__ == "__main__":
    unittest.main()
