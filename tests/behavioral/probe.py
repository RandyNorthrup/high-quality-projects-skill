"""Independent executable product oracle for isolated order-library trials."""

import argparse
import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


def behavior(region: str) -> None:
    """Check public results against explicit domain examples and canonical delegation."""
    quantity = importlib.import_module("src.quantity")
    with patch.object(quantity, "quantity", return_value=73) as canonical:
        orders = importlib.import_module("src.orders")
        observed = orders.create_order(12)
        if observed != {"quantity": 73} or canonical.call_args != ((12,), {}):
            message = "Order API does not delegate to the canonical quantity owner."
            raise AssertionError(message)
    orders = importlib.reload(orders)
    for value in (0, 1, 7, 1000000):
        if orders.create_order(value) != {"quantity": value}:
            message = f"Wrong order result for {value!r}"
            raise AssertionError(message)
    for value, error in (
        (-1, ValueError),
        (-100, ValueError),
        (True, TypeError),
        (False, TypeError),
        (1.5, TypeError),
        ("7", TypeError),
        (None, TypeError),
        ([], TypeError),
    ):
        try:
            orders.create_order(value)
        except error:
            continue
        message = f"Missing {error.__name__} for {value!r}"
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
