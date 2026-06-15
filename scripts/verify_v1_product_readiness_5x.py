#!/usr/bin/env python3
"""
verify_v1_product_readiness_5x.py — Runs the V1 acceptance scenario 5 times.

All 5 runs must pass for V1 product readiness to be confirmed.
Expected output: "GIRAFFE V1 PRODUCT READINESS: 5/5 PASS"

Usage:
    BASE_URL=http://localhost:8000 uv run python scripts/verify_v1_product_readiness_5x.py
"""

import asyncio
import sys
import os
import importlib.util
from pathlib import Path

# Load acceptance script as module
_script_path = Path(__file__).parent / "run_v1_acceptance_apparel_order.py"
spec = importlib.util.spec_from_file_location("acceptance", _script_path)
acceptance_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance_mod)

RUNS = 5


async def main():
    print("=" * 60)
    print(f"GIRAFFE V1 PRODUCT READINESS — {RUNS}x ACCEPTANCE RUNS")
    print("=" * 60)

    results = []
    for i in range(1, RUNS + 1):
        print(f"\n--- Run {i}/{RUNS} ---")
        try:
            passed = await acceptance_mod.run_acceptance()
            results.append(passed)
            print(f"Run {i}: {'PASS' if passed else 'FAIL'}")
        except Exception as e:
            print(f"Run {i}: FAIL — {e}")
            results.append(False)

    passed_count = sum(results)
    print("\n" + "=" * 60)
    print(f"Results: {passed_count}/{RUNS} PASS")
    print("=" * 60)

    if passed_count == RUNS:
        print(f"GIRAFFE V1 PRODUCT READINESS: {RUNS}/{RUNS} PASS")
    else:
        print(f"GIRAFFE V1 PRODUCT READINESS: {passed_count}/{RUNS} PASS — FAIL")
    print("=" * 60)

    return passed_count == RUNS


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
