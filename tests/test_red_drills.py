"""Prove the regression suites reject defects in the validator, checker, and oracle themselves.

Each drill breaks one behavior in a disposable copy of the source, leaves the
test and its expected result untouched, requires that test to fail with an
assertion, restores the exact bytes (hash compared), and requires green again.
"""

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = "tests.test_verify_delivery.DeliveryTests"
PRACTICES = "tests.test_practices.PracticeCommandTests"
ORACLE = "tests.test_behavioral_checks.OutcomeOracleTests"

# (file, exact anchor, replacement, test that must fail)
DRILLS = (
    (
        "scripts/delivery/checks.py",
        " or proof.mutated_exit <= 0",
        "",
        f"{DELIVERY}.test_surviving_mutation",
    ),
    (
        "scripts/delivery/checks.py",
        'if stage not in {"readiness", "closure", "resume"}:',
        "if False:",
        f"{DELIVERY}.test_unknown_stage",
    ),
    (
        "scripts/practices/python_rules.py",
        '    "unittest.mock": "mock",\n',
        "",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/python_rules.py",
        "return bool(kinds) and all(kinds) and calls <= INSPECTION_CALLS",
        "return False and all(kinds) and calls <= INSPECTION_CALLS",
        f"{PRACTICES}.test_tests_must_be_able_to_fail_a_user",
    ),
    (
        "scripts/practices/cli.py",
        "if allowance and finding.check in ALLOWABLE_CHECKS and allowance.reason:",
        "if allowance and finding.check in ALLOWABLE_CHECKS:",
        f"{PRACTICES}.test_allowances_are_reviewed_exceptions",
    ),
    (
        "scripts/practices/workflows.py",
        'if "pull_request" in workflow.triggers and "merge_group" not in workflow.triggers:',
        "if False:",
        f"{PRACTICES}.test_merge_gate_workflows",
    ),
    (
        "scripts/practices/upstreams.py",
        "if age > item.max_age_days:",
        "if False:",
        f"{PRACTICES}.test_upstream_currency",
    ),
    (
        "scripts/practices/register.py",
        "if Path(relative).suffix.lower() in DOCUMENT_SUFFIXES:",
        "if False:",
        f"{PRACTICES}.test_pitfalls_register_is_enforced_by_code",
    ),
    (
        "scripts/practices/python_rules.py",
        "if bases & HANDLER_BASES:",
        "if False:",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/python_rules.py",
        '    "fakeredis": "stand-in",\n',
        "",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/python_rules.py",
        'if name.rsplit(".", 1)[-1] == "flaky":',
        "if False:",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/script_rules.py",
        r'r"\b(?:vi|jest)\s*\.\s*(?:mock|doMock',
        r'r"\b(?:vi|jest)\s*\.\s*(?:unmatched|doMock',
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/masking.py",
        "self.blank(self.index, stop, comment=True)",
        "pass",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/family_rules.py",
        "for pattern, check in IMPORT_RULES.get(source.language, ())",
        "for pattern, check in ()",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/family_rules.py",
        "if PESTER_MOCK.match(code):",
        "if False:",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/manifests.py",
        "if item in SCRIPT_PACKAGES",
        "if False",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/python_rules.py",
        "if len(copies) >= ONE_OFF_COPIES:",
        "if False:",
        f"{PRACTICES}.test_tests_must_be_able_to_fail_a_user",
    ),
    (
        "scripts/practices/python_rules.py",
        'if self.source.is_test and name == "sleep" and owner in {"", *SLEEP_OWNERS}:',
        "if False:",
        f"{PRACTICES}.test_waits_timeouts_and_retries",
    ),
    (
        "scripts/practices/script_rules.py",
        "and NUMBER_ARGUMENT.fullmatch(text) is not None",
        "and False",
        f"{PRACTICES}.test_waits_timeouts_and_retries",
    ),
    (
        "scripts/practices/workflows.py",
        r'if re.match(r"^\s+paths(?:-ignore)?\s*:", workflow.lines[index]):',
        "if False:",
        f"{PRACTICES}.test_merge_gate_workflows",
    ),
    (
        "scripts/practices/workflows.py",
        'if SECRET_USE.search(line.split("#", 1)[0]):',
        "if False:",
        f"{PRACTICES}.test_merge_gate_workflows",
    ),
    (
        "scripts/practices/workflows.py",
        'if not job_level(body, "timeout-minutes") and not job_level(body, "uses"):',
        "if False:",
        f"{PRACTICES}.test_merge_gate_workflows",
    ),
    (
        "scripts/practices/upstreams.py",
        (
            'elif item.latest_seen.removeprefix("v") != item.pinned.removeprefix("v")'
            " and not item.hold:"
        ),
        "elif False:",
        f"{PRACTICES}.test_upstream_currency",
    ),
    (
        "scripts/practices/upstreams.py",
        "if text is None or item.pinned not in text:",
        "if False:",
        f"{PRACTICES}.test_upstream_currency",
    ),
    (
        "scripts/practices/upstreams.py",
        'return tag.removeprefix("v")',
        "return tag",
        f"{PRACTICES}.test_release_watch_queries_github_live",
    ),
    (
        "scripts/practices/register.py",
        'return [Finding(rules, 1, "register-missing", message)]',
        "return []",
        f"{PRACTICES}.test_pitfalls_register_is_enforced_by_code",
    ),
    (
        "scripts/practices/error_rules.py",
        "if emits_message(nodes) and not keeps_cause(handler, nodes):",
        "if False:",
        f"{PRACTICES}.test_errors_name_their_cause",
    ),
    (
        "scripts/practices/error_rules.py",
        "if handler.name and isinstance(node, ast.Name) and node.id == handler.name:",
        "if False:",
        f"{PRACTICES}.test_errors_name_their_cause",
    ),
    (
        "scripts/practices/error_rules.py",
        "return masked.code[start:end] != bare or EMITS.search(bare) is not None",
        "return False",
        f"{PRACTICES}.test_errors_name_their_cause",
    ),
    (
        "scripts/practices/error_rules.py",
        "if RETHROW.search(bare):",
        "if False:",
        f"{PRACTICES}.test_errors_name_their_cause",
    ),
    (
        "scripts/practices/python_rules.py",
        "if DOUBLE_CLASS.match(node.name) and not bases & HANDLER_BASES:",
        "if False:",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/python_rules.py",
        '(name == "type" and len(value.args) == TYPE_BUILDER_ARGS)',
        '(name == "type")',
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/script_rules.py",
        r'rf"\bclass\s+(?:{DOUBLE_PREFIXES})',
        r'rf"\bunmatched\s+(?:{DOUBLE_PREFIXES})',
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/script_rules.py",
        r'r"|\b(?:const|let|var)\s+(?:fake|stub',
        r'r"|\b(?:unmatched)\s+(?:fake|stub',
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/script_rules.py",
        r'r"\bcreate(?:Secure)?Server\s*\(',
        r'r"\bunmatchedServer\s*\(',
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/family_rules.py",
        "for pattern in (DOUBLE_TYPE, GO_DOUBLE_TYPE)",
        "for pattern in ()",
        f"{PRACTICES}.test_test_doubles_are_refused_in_every_language",
    ),
    (
        "scripts/practices/parallel_rules.py",
        "if STASH.search(words):",
        "if False:",
        f"{PRACTICES}.test_parallel_work_and_local_hooks",
    ),
    (
        "scripts/practices/parallel_rules.py",
        "if BASE_WORKTREE.search(words):",
        "if False:",
        f"{PRACTICES}.test_parallel_work_and_local_hooks",
    ),
    (
        "scripts/practices/parallel_rules.py",
        r'r"worktree\s+add\b(?![^\n;&|]*\s(?:-b|-B|--detach|-d)(?=\s|$))"',
        r'r"worktree\s+add\b"',
        f"{PRACTICES}.test_parallel_work_and_local_hooks",
    ),
    (
        "scripts/practices/parallel_rules.py",
        "if isinstance(node, ast.Call) and called_name(node) in PROCESS_CALLS:",
        "if False:",
        f"{PRACTICES}.test_parallel_work_and_local_hooks",
    ),
    (
        "scripts/practices/parallel_rules.py",
        "and any(IGNORES_CHANGES.match(line) for line in item)",
        "and True",
        f"{PRACTICES}.test_parallel_work_and_local_hooks",
    ),
    (
        "scripts/practices/parallel_rules.py",
        "if WHOLE_SUITE.search(line.translate(SEPARATORS)):",
        "if False:",
        f"{PRACTICES}.test_parallel_work_and_local_hooks",
    ),
    (
        "tests/behavioral/probe.py",
        " or 12 not in arguments",
        "",
        f"{ORACLE}.test_duplicate_implementation_rejected",
    ),
)


class RedDrills(unittest.TestCase):
    """Reuse the real suites in a disposable source copy without changing their assertions."""

    def test_defects_are_caught_and_restored(self) -> None:
        """Require baseline green, the intended assertion, byte restoration, and green again."""
        with tempfile.TemporaryDirectory(prefix="red-drill-") as temporary:
            workspace = Path(temporary)
            self.assertTrue(
                workspace.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
            )
            for directory in ("scripts", "tests", "templates"):
                shutil.copytree(
                    ROOT / directory,
                    workspace / directory,
                    ignore=shutil.ignore_patterns("__pycache__", ".mypy_cache", ".ruff_cache"),
                )
            shutil.copyfile(ROOT / "AGENTS.md", workspace / "AGENTS.md")
            for test in sorted({drill[3] for drill in DRILLS}):
                baseline = self.run_test(workspace, test)
                self.assertEqual(baseline.returncode, 0, baseline.stdout)
            for relative, before, after, test in DRILLS:
                with self.subTest(file=relative, test=test):
                    source = workspace / relative
                    original = source.read_bytes()
                    digest = hashlib.sha256(original).hexdigest()
                    text = original.decode("utf-8")
                    self.assertEqual(text.count(before), 1, "Mutation anchor drifted")
                    try:
                        source.write_bytes(text.replace(before, after).encode("utf-8"))
                        red = self.run_test(workspace, test)
                        self.assertNotEqual(red.returncode, 0, f"Defect survived:\n{red.stdout}")
                        self.assertIn(test.rsplit(".", 1)[-1], red.stdout)
                        self.assertIn("AssertionError", red.stdout)
                    finally:
                        source.write_bytes(original)
                        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
                    restored = self.run_test(workspace, test)
                    self.assertEqual(restored.returncode, 0, restored.stdout)

    @staticmethod
    def run_test(workspace: Path, test: str) -> subprocess.CompletedProcess[str]:
        """Run one unmodified test with a fresh interpreter and no cached bytecode."""
        # The interpreter, module, test identity, and owned cwd are fixed by this
        # harness. No shell or outside command string participates in execution.
        return subprocess.run(  # noqa: S603  # nosec B603
            [sys.executable, "-B", "-m", "unittest", "-v", test],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
