"""giraffe-db unified ID contract in GPM/GLTG traces.

giraffe-agent uses its own (uuid-based) entity id namespace and does not mint
giraffe-db record ids. These tests pin two things:

1. No retired giraffe-db legacy id (``<ENTITY>_SYN_<digits>``) survives anywhere
   in the repo's GPM/GLTG/trace surfaces (cross-repo scanner, error tier).
2. When a canonical giraffe-db record id flows through a GLTG lead-time trace,
   it is carried verbatim -- never rewritten to a legacy form.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from src.lead_time.models import LeadTimePath, LeadTimeScenario

_REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_RE = re.compile(r"^GDB_SYN_V1_(?:SUP|PROD|CAP|CUST|PREF|RFQ|QUOTE|OBS|RISK)_[0-9]{6}$")
LEGACY_RE = re.compile(r"_SYN_[0-9]{3,}$")


def test_no_legacy_giraffe_db_ids_in_repo():
    result = subprocess.run(
        [sys.executable, "scripts/check_unified_data_ids.py", "--repo", "."],
        cwd=_REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RESULT: PASS" in result.stdout


def test_gltg_leadtime_trace_preserves_canonical_supplier_id():
    canonical = "GDB_SYN_V1_SUP_000001"
    path = LeadTimePath(
        path_id=f"single:{canonical}",
        project_id="proj_1",
        supplier_id=canonical,
        supplier_name="Example Supplier",
    )
    assert path.supplier_id == canonical
    assert CANONICAL_RE.match(path.supplier_id)
    assert not LEGACY_RE.search(path.supplier_id)

    scenario = LeadTimeScenario(scenario_id="s1", project_id="proj_1", selected_supplier_id=canonical)
    assert scenario.selected_supplier_id == canonical
    assert CANONICAL_RE.match(scenario.selected_supplier_id)
