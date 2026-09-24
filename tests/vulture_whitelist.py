"""Names vulture cannot see being used, referenced here so mypy checks they exist.

Vulture reports these at 60% confidence because they are reached through
values, serialization, or discovery rather than attribute syntax. This follows
vulture's whitelist idiom of bare attribute expressions, placed under
TYPE_CHECKING: mypy verifies each reference and nothing executes it. A renamed
or removed name fails type checking instead of leaving a stale allowance
behind. Add an entry only together with the reason it is reachable.
"""

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from typing import Any

    from scripts.delivery.model import (
        Acceptance,
        ChangeAction,
        Checkpoint,
        Evidence,
        PendingOperation,
        RedProof,
        Requirement,
        ResultStatus,
        RuleSource,
        TaskStatus,
        Work,
    )
    from tests.test_delivery_red_drills import ValidatorRedDrills

    # Constructed from ledger text by value, for example TaskStatus("planned").
    TaskStatus.PLANNED
    ResultStatus.FAIL
    ResultStatus.DEFERRED
    ResultStatus.STALE
    ChangeAction.CREATE
    ChangeAction.MODIFY

    # Read through dataclasses.asdict into semantic digests and JSON reports.
    cast("RuleSource", None).revision
    cast("Work", None).title
    cast("Requirement", None).statement
    cast("Acceptance", None).given
    cast("Acceptance", None).when
    cast("Acceptance", None).then
    cast("RedProof", None).mutation
    cast("Evidence", None).method
    cast("PendingOperation", None).description
    cast("Checkpoint", None).source_revision

    # CaseResult keys are written as dictionary literals. mypy checks those
    # literals against the TypedDict itself; these names exist for vulture.
    cast("Any", None).mechanical_pass
    cast("Any", None).semantic_review

    # unittest discovers test classes by name.
    ValidatorRedDrills
