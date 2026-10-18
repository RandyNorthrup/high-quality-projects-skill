#!/usr/bin/env python3
"""Refuse practices that let a project pass its gates while users are harmed.

Requires Python 3.12+ and only its standard library. Exit 0 means every check ran
and nothing was refused; exit 1 lists refused practices; exit 2 means the root,
upstreams.json, or the pitfalls register could not be read.
With --watch it instead asks each watched upstream for its latest release and
exits 1 when one moved since the last review.
"""

import sys

from practices.cli import run


def main() -> int:
    """Print the report and propagate its exact result."""
    code, output = run()
    print(output)
    return code


if __name__ == "__main__":
    sys.exit(main())
