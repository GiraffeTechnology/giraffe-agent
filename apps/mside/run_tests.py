#!/usr/bin/env python3
"""
M-side integration test runner.

Run from apps/mside/:
    python run_tests.py
"""
import sys
import os
import subprocess
from pathlib import Path

# Ensure repo root is on path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

if __name__ == "__main__":
    print("\nGiraffe Agent M-side Integration Tests")
    print("Running pytest suite from:", Path(__file__).parent)
    print("=" * 50)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONPATH": str(repo_root)},
    )
    sys.exit(result.returncode)
