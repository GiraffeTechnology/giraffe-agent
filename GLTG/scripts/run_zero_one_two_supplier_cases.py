"""Validates the zero/one/two supplier edge cases for the GLTG engine.

Run from the GLTG/ directory:
    uv run python scripts/run_zero_one_two_supplier_cases.py
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
EXAMPLES = ROOT / "examples"

from gltg.integrations.json_io import load_order_from_json
from gltg.engine import LeadTimeGraphEngine
from gltg.models.enums import FeasibilityStatus, RiskFlagCode


def run_case(label: str, json_file: str, engine: LeadTimeGraphEngine):
    print(f"\n{'=' * 60}")
    print(f"CASE: {label}")
    print(f"{'=' * 60}")
    order_path = EXAMPLES / json_file
    print(f"Loading: {order_path}")
    order = load_order_from_json(order_path)
    print(f"  order_id    : {order.order_id}")
    print(f"  quantity    : {order.quantity:,}")
    print(f"  participants: {len(order.participants)}")
    packet = engine.evaluate(order)
    print(f"  status      : {packet.status.value}")
    print(f"  options     : {len(packet.options)}")
    print(f"  risk_flags  : {[rf.code.value for rf in packet.risk_flags]}")
    return packet


def main() -> None:
    print("GLTG ZERO/ONE/TWO SUPPLIER CASES")
    engine = LeadTimeGraphEngine()

    # ------------------------------------------------------------------ #
    # Case 1: Zero suppliers — expect NO_FEASIBLE_OPTION, 0 options       #
    # ------------------------------------------------------------------ #
    packet_zero = run_case(
        "Zero suppliers (ORD-ZERO-001)",
        "zero_suppliers.json",
        engine,
    )

    assert packet_zero.status == FeasibilityStatus.NO_FEASIBLE_OPTION, (
        f"FAIL zero: expected NO_FEASIBLE_OPTION, got {packet_zero.status}"
    )
    print("  [PASS] status == NO_FEASIBLE_OPTION")

    assert len(packet_zero.options) == 0, (
        f"FAIL zero: expected 0 options, got {len(packet_zero.options)}"
    )
    print("  [PASS] options == 0")

    # ------------------------------------------------------------------ #
    # Case 2: One supplier — expect LIMITED_OPTIONS, 1 option,            #
    #         LIMITED_COMPETITION in risk_flags                           #
    # ------------------------------------------------------------------ #
    packet_one = run_case(
        "One supplier (ORD-ONE-001)",
        "one_supplier.json",
        engine,
    )

    assert packet_one.status == FeasibilityStatus.LIMITED_OPTIONS, (
        f"FAIL one: expected LIMITED_OPTIONS, got {packet_one.status}"
    )
    print("  [PASS] status == LIMITED_OPTIONS")

    assert len(packet_one.options) == 1, (
        f"FAIL one: expected 1 option, got {len(packet_one.options)}"
    )
    print("  [PASS] options == 1")

    risk_codes_one = {rf.code for rf in packet_one.risk_flags}
    assert RiskFlagCode.LIMITED_COMPETITION in risk_codes_one, (
        f"FAIL one: LIMITED_COMPETITION not in risk_flags: {risk_codes_one}"
    )
    print("  [PASS] LIMITED_COMPETITION in risk_flags")

    # ------------------------------------------------------------------ #
    # Case 3: Two suppliers — expect LIMITED_OPTIONS, 2 options,          #
    #         LIMITED_COMPARISON in risk_flags                            #
    # ------------------------------------------------------------------ #
    packet_two = run_case(
        "Two suppliers (ORD-TWO-001)",
        "two_suppliers.json",
        engine,
    )

    assert packet_two.status == FeasibilityStatus.LIMITED_OPTIONS, (
        f"FAIL two: expected LIMITED_OPTIONS, got {packet_two.status}"
    )
    print("  [PASS] status == LIMITED_OPTIONS")

    assert len(packet_two.options) == 2, (
        f"FAIL two: expected 2 options, got {len(packet_two.options)}"
    )
    print("  [PASS] options == 2")

    risk_codes_two = {rf.code for rf in packet_two.risk_flags}
    assert RiskFlagCode.LIMITED_COMPARISON in risk_codes_two, (
        f"FAIL two: LIMITED_COMPARISON not in risk_flags: {risk_codes_two}"
    )
    print("  [PASS] LIMITED_COMPARISON in risk_flags")

    print()
    print("GLTG ZERO/ONE/TWO SUPPLIER CASES: PASS")


if __name__ == "__main__":
    main()
