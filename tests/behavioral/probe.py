"""Independent executable product oracle for isolated order-library trials."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import CodeType, FrameType


def observe_calls(code: CodeType, action: Callable[[], object]) -> tuple[object, list[object]]:
    """Run the real action and record the first argument of every call into `code`.

    A profiling hook only observes; the canonical helper keeps running, so the
    oracle checks the real result rather than a value a test double supplied.
    """
    arguments: list[object] = []

    def profile(frame: FrameType, event: str, _value: object) -> None:
        if event == "call" and frame.f_code is code:
            arguments.append(next(iter(frame.f_locals.values()), None))

    sys.setprofile(profile)
    try:
        result = action()
    finally:
        sys.setprofile(None)
    return result, arguments


def behavior(region: str) -> None:
    """Check public results against explicit domain examples and canonical delegation."""
    quantity = importlib.import_module("src.quantity")
    orders = importlib.import_module("src.orders")
    observed, arguments = observe_calls(quantity.quantity.__code__, lambda: orders.create_order(12))
    if observed != {"quantity": quantity.quantity(12)} or 12 not in arguments:
        message = "Order API does not delegate to the canonical quantity owner."
        raise AssertionError(message)
    for value in (0, 1, 7, 1000000):
        if orders.create_order(value) != {"quantity": value}:
            message = f"Wrong order result for {value!r}"
            raise AssertionError(message)
    rejected: tuple[tuple[object, type[Exception]], ...] = (
        (-1, ValueError),
        (-100, ValueError),
        (True, TypeError),
        (False, TypeError),
        (1.5, TypeError),
        ("7", TypeError),
        (None, TypeError),
        ([], TypeError),
    )
    for invalid, error in rejected:
        try:
            orders.create_order(invalid)
        except error:
            continue
        message = f"Missing {error.__name__} for {invalid!r}"
        raise AssertionError(message)
    if orders.default_region() != region:
        message = "Existing region behavior was not preserved."
        raise AssertionError(message)


def main() -> int:
    """Run one independently selected oracle in a fresh process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--mode", choices=("behavior", "tests"), required=True)
    parser.add_argument("--region", default="east")
    args = parser.parse_args()
    sys.path.insert(0, str(args.root.resolve(strict=True)))
    if args.mode == "behavior":
        behavior(args.region)
        return 0
    suite = unittest.defaultTestLoader.discover(str(args.root / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.stdout.write(
        json.dumps(
            {
                "tests": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
            }
        )
        + "\n"
    )
    return 0 if result.wasSuccessful() and result.testsRun else 1


if __name__ == "__main__":
    raise SystemExit(main())
