"""GLTG command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_evaluate(args: argparse.Namespace) -> None:
    """Run the evaluate pipeline on an order JSON file."""
    from ..engine import LeadTimeGraphEngine
    from .json_io import load_order_from_json, save_packet_to_json
    from ..packets.serializers import serialize_packet

    order = load_order_from_json(args.order)
    engine = LeadTimeGraphEngine()
    packet = engine.evaluate(order)

    if args.output:
        save_packet_to_json(packet, args.output)
        print(f"Packet saved to {args.output}")
    elif args.summary:
        _print_summary(packet)
    else:
        print(json.dumps(serialize_packet(packet), indent=2))


def _cmd_reforecast(args: argparse.Namespace) -> None:
    """Run reforecast on an existing packet with new events."""
    from ..engine import LeadTimeGraphEngine
    from .json_io import load_events_from_json, save_packet_to_json
    from ..packets.serializers import deserialize_packet, serialize_packet
    import json as _json

    # Load existing packet
    packet_data = _json.loads(Path(args.packet).read_text(encoding="utf-8"))
    packet = deserialize_packet(packet_data)

    events = load_events_from_json(args.events)

    engine = LeadTimeGraphEngine()
    updated = engine.reforecast(packet, events)

    if args.output:
        save_packet_to_json(updated, args.output)
        print(f"Updated packet saved to {args.output}")
    elif args.summary:
        _print_summary(updated)
    else:
        print(_json.dumps(serialize_packet(updated), indent=2))


def _print_summary(packet) -> None:
    """Print a human-readable summary of a packet."""
    print(f"\nOrder:        {packet.order_id}")
    print(f"Status:       {packet.status.value}")
    print(f"Commitable:   {packet.commitable_date}")
    print(f"Most Likely:  {packet.most_likely_date}")
    print(f"On-Time Prob: {f'{packet.on_time_probability:.0%}' if packet.on_time_probability else 'N/A'}")
    print(f"Options:      {len(packet.options)}")
    print(f"Risk Flags:   {len(packet.risk_flags)}")
    print(f"Missing:      {', '.join(packet.missing_fields) or 'None'}")
    if packet.recommended_action:
        print(f"Action:       {packet.recommended_action}")
    if packet.options:
        print("\nTop Options:")
        for i, opt in enumerate(packet.options, 1):
            label = opt.label.value if opt.label else "-"
            print(
                f"  {i}. [{label}] commitable={opt.commitable_date}  "
                f"otp={f'{opt.on_time_probability:.0%}' if opt.on_time_probability else 'N/A'}  "
                f"score={opt.score:.3f}" if opt.score else f"  {i}. [{label}] commitable={opt.commitable_date}"
            )
    print()


def main(argv: list[str] | None = None) -> None:
    """Entry point for the `gltg` CLI command."""
    parser = argparse.ArgumentParser(
        prog="gltg",
        description="Giraffe Lead-Time Graph — apparel order feasibility engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # evaluate command
    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate an apparel order and produce a feasibility packet",
    )
    eval_parser.add_argument("order", help="Path to order JSON file")
    eval_parser.add_argument("-o", "--output", help="Save packet to this JSON file")
    eval_parser.add_argument(
        "--summary", action="store_true", help="Print a human-readable summary"
    )
    eval_parser.set_defaults(func=_cmd_evaluate)

    # reforecast command
    rf_parser = subparsers.add_parser(
        "reforecast",
        help="Reforecast an existing packet with new progress events",
    )
    rf_parser.add_argument("packet", help="Path to existing packet JSON file")
    rf_parser.add_argument("events", help="Path to progress events JSON file")
    rf_parser.add_argument("-o", "--output", help="Save updated packet to this JSON file")
    rf_parser.add_argument(
        "--summary", action="store_true", help="Print a human-readable summary"
    )
    rf_parser.set_defaults(func=_cmd_reforecast)

    parsed = parser.parse_args(argv)
    try:
        parsed.func(parsed)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
