"""Verifies GLTG evaluation determinism by running 5 evaluations and comparing results.

Run from the GLTG/ directory:
    uv run python scripts/verify_gltg_5x.py
"""

import sys
import pathlib
from datetime import timedelta

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
EXAMPLES = ROOT / "examples"

from gltg.integrations.json_io import load_order_from_json
from gltg.engine import LeadTimeGraphEngine


def main() -> None:
    print("=" * 60)
    print("GLTG 5X DETERMINISM VERIFICATION")
    print("=" * 60)

    order_path = EXAMPLES / "10000_shirts_order.json"
    print(f"\nLoading order from: {order_path}")
    order = load_order_from_json(order_path)
    print(f"  order_id : {order.order_id}")
    print(f"  quantity : {order.quantity:,}")

    engine = LeadTimeGraphEngine()

    results = []
    print("\nRunning 5 evaluations ...")
    for i in range(1, 6):
        packet = engine.evaluate(order)
        results.append(packet)
        print(
            f"  Run {i}: status={packet.status.value}  "
            f"options={len(packet.options)}  "
            f"commitable={packet.commitable_date}"
        )

    print("\nComparing results ...")

    # Assert same status across all runs
    statuses = [p.status for p in results]
    assert len(set(statuses)) == 1, (
        f"FAIL: statuses differ across runs: {[s.value for s in statuses]}"
    )
    print(f"  [PASS] All 5 runs have the same status: {statuses[0].value}")

    # Assert same number of options across all runs
    option_counts = [len(p.options) for p in results]
    assert len(set(option_counts)) == 1, (
        f"FAIL: option counts differ across runs: {option_counts}"
    )
    print(f"  [PASS] All 5 runs have the same option count: {option_counts[0]}")

    # Assert commitable dates are within 1 calendar day of each other
    # (since date.today() is stable within a single run)
    commitable_dates = [p.commitable_date for p in results]
    non_null = [d for d in commitable_dates if d is not None]

    if non_null:
        min_date = min(non_null)
        max_date = max(non_null)
        spread = (max_date - min_date).days
        assert spread <= 1, (
            f"FAIL: commitable_date spread is {spread} days (min={min_date}, max={max_date}). "
            f"All dates: {commitable_dates}"
        )
        print(
            f"  [PASS] commitable_date spread <= 1 day: "
            f"min={min_date}, max={max_date}, spread={spread}d"
        )
    else:
        # All None is also consistent
        assert all(d is None for d in commitable_dates), (
            f"FAIL: mixed None/not-None commitable_dates: {commitable_dates}"
        )
        print("  [PASS] All commitable_dates are None (consistent)")

    print()
    print("GLTG 5X VERIFICATION: PASS")


if __name__ == "__main__":
    main()
