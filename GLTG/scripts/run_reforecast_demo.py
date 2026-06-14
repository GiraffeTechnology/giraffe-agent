"""Demonstrates the reforecast API using the 10,000-shirts order.

Run from the GLTG/ directory:
    uv run python scripts/run_reforecast_demo.py
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
EXAMPLES = ROOT / "examples"

from gltg.integrations.json_io import load_order_from_json, load_events_from_json
from gltg.engine import LeadTimeGraphEngine


def main() -> None:
    print("=" * 60)
    print("GLTG REFORECAST DEMO")
    print("=" * 60)

    # Step 1: Load the order and evaluate initial packet
    order_path = EXAMPLES / "10000_shirts_order.json"
    print(f"\nStep 1: Loading order from {order_path}")
    order = load_order_from_json(order_path)
    print(f"  order_id : {order.order_id}")
    print(f"  quantity : {order.quantity:,}")

    engine = LeadTimeGraphEngine()
    print("\nStep 2: Evaluating initial packet ...")
    initial_packet = engine.evaluate(order)

    initial_commitable = initial_packet.commitable_date
    initial_status = initial_packet.status.value
    initial_options = len(initial_packet.options)

    print(f"  status         : {initial_status}")
    print(f"  commitable_date: {initial_commitable}")
    print(
        f"  on_time_prob   : "
        f"{f'{initial_packet.on_time_probability:.0%}' if initial_packet.on_time_probability is not None else 'N/A'}"
    )
    print(f"  options        : {initial_options}")
    print(f"  risk_flags     : {[rf.code.value for rf in initial_packet.risk_flags]}")

    # Step 3: Load progress events
    events_path = EXAMPLES / "10000_shirts_progress_events.json"
    print(f"\nStep 3: Loading progress events from {events_path}")
    events = load_events_from_json(events_path)
    print(f"  Loaded {len(events)} event(s):")
    for evt in events:
        print(f"    [{evt.event_id}] {evt.event_type.value} on {evt.event_date}  payload={evt.payload}")

    # Step 4: Reforecast
    print("\nStep 4: Running engine.reforecast(packet, events) ...")
    updated_packet = engine.reforecast(initial_packet, events)

    new_commitable = updated_packet.commitable_date

    # Compute delta
    delta_str = "N/A"
    if initial_commitable and new_commitable:
        delta = (new_commitable - initial_commitable).days
        sign = "+" if delta >= 0 else ""
        delta_str = f"{sign}{delta} days"

    print(f"\nBefore reforecast commitable date : {initial_commitable}")
    print(f"After  reforecast commitable date : {new_commitable}")
    print(f"Delta                             : {delta_str}")
    print(
        f"On-time probability (updated)     : "
        f"{f'{updated_packet.on_time_probability:.0%}' if updated_packet.on_time_probability is not None else 'N/A'}"
    )
    print(f"Critical path changed             : {updated_packet.critical_path != initial_packet.critical_path}")
    new_flag_codes = [rf.code.value for rf in updated_packet.risk_flags]
    print(f"Risk flags (updated)              : {new_flag_codes}")

    if updated_packet.options:
        print("\nUpdated top option:")
        opt = updated_packet.options[0]
        label = opt.label.value if opt.label else "-"
        print(f"  [{label}]  commitable={opt.commitable_date}  most_likely={opt.most_likely_date}")

    print()
    print("GLTG REFORECAST DEMO: COMPLETE")


if __name__ == "__main__":
    main()
