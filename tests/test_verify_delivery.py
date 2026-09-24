"""Exercise native delivery validation against positive and deliberately broken records."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import override

from scripts.delivery.checks import validate
from scripts.delivery.graph import check_graph
from scripts.delivery.model import EvidenceKind
from scripts.delivery.reader import PlanError, load_plan, parse_json, read_environment, read_ledger
from scripts.delivery.snapshot import input_paths, semantic_digest
from tests.delivery_fixtures import (
    FixtureData,
    complete,
    environment,
    native_ledger,
    ready,
    save,
)

ROOT = Path(__file__).resolve().parents[1]


class DeliveryTests(unittest.TestCase):
    """Require expected diagnostics, preserved inputs, and genuinely distinct stages."""

    @override
    def setUp(self) -> None:
        """Create an isolated owned workspace for each case."""
        self.temporary = tempfile.TemporaryDirectory(prefix="delivery-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def codes(self, data: FixtureData, stage: str = "closure") -> set[str]:
        """Return the diagnostic identities produced by the real validator."""
        report = validate(
            native_ledger(data), self.root, stage, read_environment(environment(), "context")
        )
        return {finding.code for finding in report.findings}

    def test_ready_is_not_complete(self) -> None:
        """A reviewed plan may be ready while its implementation remains open."""
        data = ready(self.root)
        self.assertEqual(self.codes(data, "readiness"), set())
        self.assertIn("task-unverified", self.codes(data))

    def test_shipped_record_shapes(self) -> None:
        """Compact, feature, and retrofit examples use one valid relationship contract."""
        fixture_root = ROOT / "tests/fixtures/delivery"
        for name in ("compact", "feature", "retrofit"):
            with self.subTest(shape=name):
                data = parse_json((fixture_root / f"{name}.json").read_text(encoding="utf-8"))
                self.assertEqual(check_graph(read_ledger(data)), [])

    def test_template_does_not_claim_readiness(self) -> None:
        """A copied scaffold has no actual readiness evidence and cannot pass as delivered work."""
        _, ledger = load_plan(ROOT / "templates/workflow/PLAN.md")
        report = validate(ledger, ROOT, "readiness", read_environment(environment(), "context"))
        self.assertFalse(report.passed)
        self.assertIn("evidence-coverage", {finding.code for finding in report.findings})

    def test_complete_and_resume(self) -> None:
        """Complete evidence supports closure and a fresh checkpoint supports resume."""
        data = complete(self.root)
        self.assertEqual(self.codes(data), set())
        self.assertEqual(self.codes(data, "resume"), set())

    def test_dangling_requirement(self) -> None:
        """A missing parent is a relationship failure rather than implicit coverage."""
        data = complete(self.root)
        data["acceptance"][0]["requirement"] = "MISSING"
        self.assertIn("dangling-reference", self.codes(data))

    def test_duplicate_record_id(self) -> None:
        """Duplicated records cannot silently overwrite one another in an index."""
        data = complete(self.root)
        data["tasks"].append(copy.deepcopy(data["tasks"][0]))
        self.assertIn("duplicate-id", self.codes(data))

    def test_dependency_cycle(self) -> None:
        """Self-dependency is rejected before completion evidence is considered."""
        data = complete(self.root)
        data["tasks"][0]["depends_on"] = ["TASK-1"]
        self.assertIn("dependency-cycle", self.codes(data))

    def test_empty_scope(self) -> None:
        """An empty work inventory cannot pass by universal-check vacuity."""
        data = complete(self.root)
        data.update(requirements=[], acceptance=[], tasks=[], evidence=[], checkpoint=None)
        self.assertIn("empty-scope", self.codes(data))

    def test_surviving_mutation(self) -> None:
        """A red run returning success fails the drill contract."""
        data = complete(self.root)
        data["evidence"][2]["red"]["mutated_exit"] = 0
        self.assertIn("red-exits", self.codes(data))

    def test_noop_mutation(self) -> None:
        """A different exit cannot substitute for an actual changed input."""
        data = complete(self.root)
        proof = data["evidence"][2]["red"]
        proof["mutated"] = copy.deepcopy(proof["before"])
        self.assertIn("red-mutation", self.codes(data))

    def test_wrong_diagnostic(self) -> None:
        """An unrelated failure is not accepted as the intended negative case."""
        data = complete(self.root)
        data["evidence"][2]["red"]["observed_diagnostic"] = "Missing dependency"
        self.assertIn("red-diagnostic", self.codes(data))

    def test_receipt_failure_cases(self) -> None:
        """Missing, stale, and invalid success metadata each fail for their own reason."""
        cases: tuple[tuple[str, object, str], ...] = (
            ("inputs", [], "inputs-stale"),
            ("artifact", None, "artifact-missing"),
            ("scope_sha256", "0" * 64, "scope-stale"),
            ("exit_code", 5, "positive-exit"),
            ("command", [], "command-missing"),
        )
        for field, value, diagnostic in cases:
            with self.subTest(field=field):
                data = complete(self.root)
                data["evidence"][1][field] = value
                self.assertIn(diagnostic, self.codes(data))

    def test_invalid_acceptance_kinds(self) -> None:
        """Review-only and incomplete test choices cannot certify behavior."""
        cases: tuple[tuple[list[str], str], ...] = (
            ([], "checks-missing"),
            (["readiness"], "readiness-not-behavior"),
            (["behavior"], "red-required"),
            (["red"], "behavior-required"),
            (["manual"], "manual-reason"),
        )
        for checks, diagnostic in cases:
            with self.subTest(checks=checks):
                data = complete(self.root)
                data["acceptance"][0]["checks"] = checks
                self.assertIn(diagnostic, self.codes(data))

    def test_artifact_tampering_and_empty_proof(self) -> None:
        """An altered or empty proof file cannot hide behind a passing status."""
        data = complete(self.root)
        artifact = self.root / "EV-TEST.log"
        artifact.write_text("Altered proof\n", encoding="utf-8")
        self.assertIn("artifact-stale", self.codes(data))
        artifact.write_bytes(b"")
        data["evidence"][1]["artifact"]["sha256"] = hashlib.sha256(b"").hexdigest()
        self.assertIn("artifact-empty", self.codes(data))

    def test_incomplete_restoration(self) -> None:
        """Restored exit zero alone does not establish restored source bytes."""
        data = complete(self.root)
        data["evidence"][2]["red"]["after"][0]["sha256"] = "0" * 64
        self.assertIn("red-restoration", self.codes(data))

    def test_recorded_command_is_not_executed(self) -> None:
        """Recorded argv remains inert data even if it contains a command with side effects."""
        data = complete(self.root)
        marker = self.root / "must-not-exist.txt"
        data["evidence"][1]["command"] = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).touch()",
        ]
        self.assertEqual(self.codes(data), set())
        self.assertFalse(marker.exists())

    def test_concurrent_active_path_ownership(self) -> None:
        """Two active tasks cannot own the same physical change path."""
        data = ready(self.root)
        task = copy.deepcopy(data["tasks"][0])
        task["id"] = "TASK-2"
        task["status"] = "active"
        data["tasks"][0]["status"] = "active"
        data["tasks"].append(task)
        self.assertIn("active-write-conflict", self.codes(data, "readiness"))

    def test_invalid_schema_inputs(self) -> None:
        """Unknown versions, types, and fields are input errors with no silent migration."""
        for value in (True, "1", 2):
            with self.subTest(version=value):
                data = complete(self.root)
                data["schema_version"] = value
                with self.assertRaises(PlanError):
                    read_ledger(data)
        data = complete(self.root)
        data["undocumented"] = True
        with self.assertRaisesRegex(PlanError, "unknown fields"):
            read_ledger(data)
        with self.assertRaisesRegex(PlanError, "invalid numeric constant"):
            parse_json('{"value": NaN}')

    def test_plan_narrative_change_invalidates_receipts(self) -> None:
        """Changes outside the JSON record still affect the reviewed delivery contract."""
        plan = save(self.root, complete(self.root))
        before = plan.read_text(encoding="utf-8")
        plan.write_text(
            before.replace(
                "# Quantity delivery", "# Quantity delivery\n\nUse a new storage architecture."
            ),
            encoding="utf-8",
        )
        _, ledger = load_plan(plan)
        report = validate(ledger, self.root, "closure", read_environment(environment(), "context"))
        self.assertIn("scope-stale", {finding.code for finding in report.findings})

    def test_plan_is_not_hashed_into_its_own_receipt(self) -> None:
        """Bind the active plan semantically without a self-referential byte hash."""
        data = complete(self.root)
        data["work"]["inputs"] = ["PLAN.md"]
        ledger = native_ledger(data)
        paths = input_paths(ledger, ("AC-1",), EvidenceKind.BEHAVIOR)
        self.assertNotIn("PLAN.md", paths)
        self.assertIn("src/quantity.py", paths)

    def test_stale_source(self) -> None:
        """Uncommitted source changes invalidate proof even without changing a Git revision."""
        data = complete(self.root)
        (self.root / "src/quantity.py").write_text(
            "def quantity(value):\n    return value\n", encoding="utf-8"
        )
        self.assertIn("inputs-stale", self.codes(data))
        self.assertIn("checkpoint-inputs-stale", self.codes(data, "resume"))

    def test_scope_change(self) -> None:
        """An altered acceptance obligation invalidates historical receipts."""
        data = complete(self.root)
        data["acceptance"][0]["then"] = "Clamp negative values to zero"
        self.assertIn("scope-stale", self.codes(data))

    def test_missing_current_context(self) -> None:
        """Receipts cannot attest their own present runtime identity."""
        ledger = native_ledger(complete(self.root))
        report = validate(ledger, self.root, "closure", None)
        self.assertIn("context-missing", {finding.code for finding in report.findings})

    def test_resume_cannot_use_readiness_as_behavior(self) -> None:
        """A reviewed specification cannot stand in for a verified implementation on resume."""
        data = complete(self.root)
        data["tasks"][0]["evidence"] = ["EV-READY"]
        self.assertIn("task-evidence-coverage", self.codes(data, "resume"))

    def test_unknown_stage(self) -> None:
        """The library rejects unsupported validation stages rather than defaulting to readiness."""
        data = complete(self.root)
        with self.assertRaisesRegex(PlanError, "unsupported stage"):
            self.codes(data, "invented-stage")

    def test_dependency_acceptance_affects_fingerprint(self) -> None:
        """A dependent claim becomes stale when its prerequisite contract changes."""
        data = complete(self.root)
        dependency = copy.deepcopy(data["tasks"][0])
        dependency.update(
            id="TASK-2",
            acceptance=["AC-2"],
            changes=[{"path": "src/policy.py", "action": "modify"}],
        )
        criterion = copy.deepcopy(data["acceptance"][0])
        criterion.update(id="AC-2", requirement="REQ-2")
        requirement = copy.deepcopy(data["requirements"][0])
        requirement.update(id="REQ-2", acceptance=["AC-2"])
        data["tasks"].append(dependency)
        data["acceptance"].append(criterion)
        data["requirements"].append(requirement)
        data["tasks"][0]["depends_on"] = ["TASK-2"]
        before = semantic_digest(native_ledger(data), ("AC-1",))
        data["acceptance"][1]["then"] = "Reject quantities above the warehouse limit"
        self.assertNotEqual(before, semantic_digest(native_ledger(data), ("AC-1",)))

    def test_progress_revision_does_not_invalidate_unchanged_scope(self) -> None:
        """A revision annotation alone cannot change semantic input identity."""
        data = complete(self.root)
        before = semantic_digest(native_ledger(data), ("AC-1",))
        data["work"]["scope_revision"] = 2
        self.assertEqual(before, semantic_digest(native_ledger(data), ("AC-1",)))

    def test_path_escape(self) -> None:
        """References outside the owning workspace are rejected before reads."""
        data = complete(self.root)
        data["work"]["inputs"] = ["../private.txt"]
        self.assertIn("path-invalid", self.codes(data))

    def test_pending_operation(self) -> None:
        """Unknown external outcomes block resume rather than being replayed."""
        data = complete(self.root)
        data["checkpoint"]["pending_operations"] = [
            {
                "id": "OP-1",
                "description": "Deployment outcome unknown",
                "next_action": "Observe deployment status",
            }
        ]
        self.assertIn("outcome-unresolved", self.codes(data, "resume"))

    def test_duplicate_json_key(self) -> None:
        """The JSON parser rejects conflicting duplicate keys."""
        with self.assertRaisesRegex(PlanError, "duplicate JSON key"):
            parse_json('{"schema_version":1,"schema_version":2}')

    def test_missing_and_duplicate_fences(self) -> None:
        """Absent and duplicated ledgers are invalid inputs, not empty successful plans."""
        path = save(self.root, ready(self.root))
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n```quality-ledger\n{}\n```\n", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "exactly one"):
            load_plan(path)
        path.write_text("# No ledger\n", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "exactly one"):
            load_plan(path)

    def test_cli_result_and_no_writes(self) -> None:
        """The actual command reports closure and leaves its plan byte-for-byte unchanged."""
        plan = save(self.root, complete(self.root))
        before = plan.read_bytes()
        # Fixed current interpreter, checked-in CLI, and owned fixture paths;
        # no shell or externally supplied command strings enter this boundary.
        result = subprocess.run(  # noqa: S603  # nosec B603
            [
                sys.executable,
                str(ROOT / "scripts/verify-delivery.py"),
                "--root",
                str(self.root),
                "--plan",
                str(plan),
                "--context",
                str(self.root / "context.json"),
                "--stage",
                "closure",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["passed"])
        self.assertEqual(plan.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
