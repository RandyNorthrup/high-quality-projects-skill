"""Name each practice check, its findings, and the input errors that stop a run."""

from dataclasses import dataclass

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT = 2


class PracticeInputError(ValueError):
    """Stop a run whose own input is missing or malformed; nothing counts as checked."""


@dataclass(frozen=True, order=True)
class Finding:
    """Locate one refused practice by file, line, and check identity."""

    path: str
    line: int
    check: str
    message: str


# A behavior-replacing double, fake timer, fake server, in-memory stand-in,
# automatic re-run, or a secret in a merge gate has no legitimate exception.
STRICT_CHECKS = frozenset({"mock", "fake-timer", "fake-server", "stand-in", "rerun", "ci-secret"})

# Name and structure heuristics can misread a legitimate case, so a reviewed
# allowance with a written reason may accept one occurrence.
ALLOWABLE_CHECKS = frozenset(
    {
        "fixed-delay",
        "timeout-override",
        "text-existence",
        "one-off",
        "ci-merge-group",
        "ci-path-filter",
        "ci-continue-on-error",
        "ci-timeout",
        "error-cause",
        "hand-written-double",
        "git-shared-state",
        "local-full-suite",
    }
)

# Data checks are fixed by correcting the data they read, never by an allowance.
DATA_CHECKS = frozenset(
    {
        "unparsed",
        "nothing-scanned",
        "upstreams-missing",
        "upstream-review-overdue",
        "upstream-behind",
        "upstream-hold-expired",
        "upstream-pin-drift",
        "upstream-released",
        "register-missing",
        "register-unenforced",
        "allowance-invalid",
        "allowance-refused",
        "allowance-unused",
    }
)

KNOWN_CHECKS = STRICT_CHECKS | ALLOWABLE_CHECKS | DATA_CHECKS
