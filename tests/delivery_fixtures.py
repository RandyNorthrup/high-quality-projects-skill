"""Build small, real filesystem fixtures for delivery-state verification."""

from __future__ import annotations

import copy
import hashlib
import json
import platform
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from scripts.delivery.model import EvidenceKind, Ledger
from scripts.delivery.reader import parse_plan
from scripts.delivery.snapshot import current_inputs, input_paths, semantic_digest

# Raw ledger JSON that tests deliberately reshape into malformed records before
# the strict reader sees it. Explicit Any is the JSON escape hatch the shared
# mypy template permits; the validator itself never receives unchecked types.
type FixtureData = dict[str, Any]


def environment() -> dict[str, object]:
    """Return the actual runtime identity used by local deterministic fixtures."""
    return {"platform": platform.system().lower(), "tools": {"python": platform.python_version()}}


def plan_text(data: FixtureData) -> str:
    """Render the one fixture plan so receipts bind its actual narrative."""
    return "# Quantity delivery\n\n```quality-ledger\n" + json.dumps(data, indent=2) + "\n```\n"


def native_ledger(data: FixtureData) -> Ledger:
    """Parse the fixture's complete source, including the narrative fingerprint."""
    return parse_plan(plan_text(data).encode("utf-8"), "PLAN.md")[1]


def initial(root: Path) -> FixtureData:
    """Create one concrete feature plan, canonical rules, and a real implementation."""
    (root / "AGENTS.md").write_text(
        "# Project rules\n\nRevision: 1\n\nValidate input before writing.\n", encoding="utf-8"
    )
    (root / "src").mkdir(exist_ok=True)
    (root / "src/quantity.py").write_text(
        "def quantity(value: int) -> int:\n"
        "    if value < 0:\n"
        "        raise ValueError('negative quantity')\n"
        "    return value\n",
        encoding="utf-8",
    )
    return {
        "schema_version": 1,
        "work": {
            "id": "WORK-1",
            "title": "Validate order quantities",
            "scope_revision": 1,
            "brief": None,
            "brief_reason": "Scoped change to an existing order parser",
            "rules": [{"path": "AGENTS.md", "revision": "1"}],
            "inputs": [],
            "environment": environment(),
        },
        "requirements": [
            {
                "id": "REQ-1",
                "statement": "Reject negative order quantities",
                "priority": "critical",
                "acceptance": ["AC-1"],
                "superseded_by": None,
            }
        ],
        "acceptance": [
            {
                "id": "AC-1",
                "requirement": "REQ-1",
                "given": "An order quantity below zero",
                "when": "The quantity is parsed",
                "then": "A negative-quantity error is raised",
                "checks": ["behavior", "red"],
                "manual_reason": None,
            }
        ],
        "tasks": [
            {
                "id": "TASK-1",
                "purpose": "Extend the canonical quantity parser",
                "acceptance": ["AC-1"],
                "depends_on": [],
                "changes": [{"path": "src/quantity.py", "action": "modify"}],
                "status": "planned",
                "evidence": [],
                "blocker": None,
                "superseded_by": None,
            }
        ],
        "evidence": [],
        "checkpoint": None,
    }


def receipt(root: Path, data: FixtureData, kind: str, identifier: str) -> FixtureData:
    """Create a deterministic receipt fixture with real hashed local artifacts."""
    ledger = native_ledger(data)
    enum = EvidenceKind(kind)
    selected = ("AC-1",)
    artifact = f"{identifier}.log"
    content = (
        "NegativeQuantityAssertion: guard omission detected\n"
        if enum == EvidenceKind.RED
        else "Fixture verification output\n"
    )
    (root / artifact).write_text(content, encoding="utf-8")
    inputs = current_inputs(root, input_paths(ledger, selected, enum))
    red = None
    if enum == EvidenceKind.RED:
        source = root / "src/quantity.py"
        original = source.read_bytes()
        original_digest = hashlib.sha256(original).hexdigest()
        mutated_digest = hashlib.sha256(original.replace(b"value < 0", b"False")).hexdigest()
        before = [{"path": "src/quantity.py", "sha256": original_digest}]
        red = {
            "mutation": "Remove the negative quantity guard",
            "baseline_exit": 0,
            "mutated_exit": 1,
            "restored_exit": 0,
            "expected_diagnostic": "NegativeQuantityAssertion",
            "observed_diagnostic": "NegativeQuantityAssertion: guard omission detected",
            "before": before,
            "mutated": [{"path": "src/quantity.py", "sha256": mutated_digest}],
            "after": copy.deepcopy(before),
        }
    return {
        "id": identifier,
        "acceptance": list(selected),
        "kind": kind,
        "status": "pass",
        "command": ["python", "-m", "unittest"]
        if enum in {EvidenceKind.BEHAVIOR, EvidenceKind.RED}
        else [],
        "method": "Record-validation fixture; agent behavior has separate evaluations",
        "environment": environment(),
        "exit_code": 0 if enum in {EvidenceKind.BEHAVIOR, EvidenceKind.RED} else None,
        "artifact": {
            "path": artifact,
            "sha256": hashlib.sha256((root / artifact).read_bytes()).hexdigest(),
        },
        "inputs": [asdict(item) for item in inputs],
        "scope_sha256": semantic_digest(ledger, selected),
        "red": red,
        "reason": None,
    }


def ready(root: Path) -> FixtureData:
    """Create a structurally complete plan with a scoped readiness-review receipt."""
    data = initial(root)
    data["evidence"] = [receipt(root, data, "readiness", "EV-READY")]
    return data


def complete(root: Path) -> FixtureData:
    """Create a complete record for testing freshness and relational validation."""
    data = ready(root)
    data["evidence"] = [
        receipt(root, data, "readiness", "EV-READY"),
        receipt(root, data, "behavior", "EV-TEST"),
        receipt(root, data, "red", "EV-RED"),
    ]
    tasks = data["tasks"]
    tasks[0]["status"] = "verified"
    tasks[0]["evidence"] = ["EV-TEST", "EV-RED"]
    ledger = native_ledger(data)
    data["checkpoint"] = {
        "scope_sha256": semantic_digest(ledger, ("AC-1",)),
        "inputs": [
            asdict(item)
            for item in current_inputs(root, input_paths(ledger, ("AC-1",), EvidenceKind.BEHAVIOR))
        ],
        "environment": environment(),
        "verified_tasks": ["TASK-1"],
        "pending_operations": [],
        "next_action": "Review the completed quantity change",
        "source_revision": None,
    }
    return data


def save(root: Path, data: FixtureData) -> Path:
    """Write the native plan plus independent observed-context fixture."""
    path = root / "PLAN.md"
    path.write_text(
        plan_text(data),
        encoding="utf-8",
    )
    (root / "context.json").write_text(json.dumps(environment()), encoding="utf-8")
    return path
