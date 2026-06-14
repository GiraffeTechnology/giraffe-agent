"""Acceptance test for the 10,000-shirts order example.

Run from the GLTG/ directory:
    uv run python scripts/run_10000_shirts_acceptance.py
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
EXAMPLES = ROOT / "examples"

from gltg.integrations.json_io import load_order_from_json
from gltg.engine import LeadTimeGraphEngine


def main() -> None:
    print("=" * 60)
    print("GLTG 10000 SHIRTS ACCEPTANCE TEST")
    print("=" * 60)

    # Step 1: Load the order
    order_path = EXAMPLES / "10000_shirts_order.json"
    print(f"\nLoading order from: {order_path}")
    order = load_order_from_json(order_path)
    print(f"  order_id       : {order.order_id}")
    print(f"  product_type   : {order.product_type}")
    print(f"  quantity       : {order.quantity:,}")
    print(f"  delivery_date  : {order.requested_delivery_date}")
    print(f"  participants   : {len(order.participants)}")
    print(f"  supplier_memory: {len(order.supplier_memory)}")

    # Step 2: Evaluate
    print("\nRunning LeadTimeGraphEngine().evaluate() ...")
    engine = LeadTimeGraphEngine()
    packet = engine.evaluate(order)

    # Step 3: Assertions
    print("\nRunning assertions ...")

    assert packet is not None, "FAIL: packet is None"
    print("  [PASS] packet is not None")

    assert packet.commitable_date is not None, (
        f"FAIL: packet.commitable_date is None (status={packet.status})"
    )
    print(f"  [PASS] commitable_date is not None: {packet.commitable_date}")

    assert len(packet.options) >= 1, (
        f"FAIL: expected >= 1 option, got {len(packet.options)} (status={packet.status})"
    )
    print(f"  [PASS] options count >= 1: {len(packet.options)}")

    assert len(packet.critical_path) >= 1, (
        f"FAIL: critical_path is empty (status={packet.status})"
    )
    print(f"  [PASS] critical_path length >= 1: {len(packet.critical_path)} nodes")

    # Step 4: Human-readable summary
    print("\n" + "-" * 60)
    print("RESULT SUMMARY")
    print("-" * 60)
    print(f"  Status           : {packet.status.value}")
    print(f"  Commitable date  : {packet.commitable_date}")
    print(f"  Most likely date : {packet.most_likely_date}")
    print(f"  Earliest date    : {packet.earliest_feasible_date}")
    print(
        f"  On-time prob     : "
        f"{f'{packet.on_time_probability:.0%}' if packet.on_time_probability is not None else 'N/A'}"
    )
    print(f"  Options          : {len(packet.options)}")
    print(f"  Critical path    : {len(packet.critical_path)} nodes")
    print(f"  Bottlenecks      : {packet.bottleneck_nodes}")
    print(f"  Risk flags       : {[rf.code.value for rf in packet.risk_flags]}")
    print(f"  Human review     : {packet.human_review_required}")
    if packet.recommended_action:
        print(f"  Recommended      : {packet.recommended_action}")

    if packet.options:
        print("\nTop Options:")
        for i, opt in enumerate(packet.options, 1):
            label = opt.label.value if opt.label else "-"
            otp = f"{opt.on_time_probability:.0%}" if opt.on_time_probability is not None else "N/A"
            score = f"{opt.score:.3f}" if opt.score is not None else "N/A"
            print(
                f"  {i}. [{label}]  commitable={opt.commitable_date}  "
                f"otp={otp}  score={score}"
            )

    print()
    print("GLTG 10000 SHIRTS ACCEPTANCE: PASS")


if __name__ == "__main__":
    main()
