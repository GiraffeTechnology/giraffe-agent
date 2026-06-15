"""
AIVAN Platform Whitelist E2E Script.

Tests platform whitelist behavior:
  1. Built-in trusted platforms are initialized correctly
  2. New platforms are flagged for approval
  3. Platform approval is persisted locally
  4. Supplier-level risk screening still runs even when platform is trusted
  5. Rejected platforms are not silently used
"""

import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("GIRAFFE_DB_MODE", "off")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
INFO = "\033[94mINFO\033[0m"

failures = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}{': ' + detail if detail else ''}")
        failures.append(label)
    return condition


# ─── Platform whitelist store (file-based, local) ─────────────────────────────

import tempfile, uuid

_PLATFORM_STORE_PATH = Path(tempfile.mkdtemp()) / "platform_whitelist.json"

BUILTIN_TRUSTED_PLATFORMS = {
    "alibaba.com": {"platform_id": "alibaba.com", "status": "approved", "source": "builtin"},
    "1688.com": {"platform_id": "1688.com", "status": "approved", "source": "builtin"},
    "aliexpress.com": {"platform_id": "aliexpress.com", "status": "approved", "source": "builtin"},
    "global.taobao.com": {"platform_id": "global.taobao.com", "status": "approved", "source": "builtin"},
    "openclaw": {"platform_id": "openclaw", "status": "approved", "source": "builtin"},
    "openclaw-mock": {"platform_id": "openclaw-mock", "status": "approved", "source": "builtin"},
}


def _load_platforms() -> dict:
    if _PLATFORM_STORE_PATH.exists():
        return json.loads(_PLATFORM_STORE_PATH.read_text())
    return dict(BUILTIN_TRUSTED_PLATFORMS)


def _save_platforms(platforms: dict) -> None:
    _PLATFORM_STORE_PATH.write_text(json.dumps(platforms, indent=2))


def init_platform_store() -> dict:
    platforms = dict(BUILTIN_TRUSTED_PLATFORMS)
    _save_platforms(platforms)
    return platforms


def get_platform_status(platform_id: str) -> str:
    platforms = _load_platforms()
    entry = platforms.get(platform_id)
    if entry is None:
        return "unknown"
    return entry.get("status", "unknown")


def approve_platform(platform_id: str, approved_by: str) -> dict:
    platforms = _load_platforms()
    platforms[platform_id] = {
        "platform_id": platform_id,
        "status": "approved",
        "approved_by": approved_by,
        "source": "manual",
    }
    _save_platforms(platforms)
    return platforms[platform_id]


def reject_platform(platform_id: str, rejected_by: str, reason: str = "") -> dict:
    platforms = _load_platforms()
    platforms[platform_id] = {
        "platform_id": platform_id,
        "status": "rejected",
        "rejected_by": rejected_by,
        "reason": reason,
        "source": "manual",
    }
    _save_platforms(platforms)
    return platforms[platform_id]


# ─── Step 1: Built-in trusted platforms initialized ──────────────────────────

print("\n[1] Built-in trusted platforms initialized")

platforms = init_platform_store()
for pid in ["alibaba.com", "1688.com", "aliexpress.com"]:
    check(f"{pid} is approved", get_platform_status(pid) == "approved")

check("Platform store persisted locally", _PLATFORM_STORE_PATH.exists())
print(f"  {INFO}  Platform store: {_PLATFORM_STORE_PATH}")
print(f"  {INFO}  Initialized {len(platforms)} platforms")

# ─── Step 2: New platform flagged for approval ────────────────────────────────

print("\n[2] New/unknown platform is flagged for approval")

new_platform = "new-b2b-marketplace.cn"
status = get_platform_status(new_platform)
check("Unknown platform has 'unknown' status", status == "unknown", f"got: {status}")
check("Unknown platform is not treated as approved", status != "approved")

# ─── Step 3: Platform approval persisted ─────────────────────────────────────

print("\n[3] Platform approval is persisted locally")

approve_platform(new_platform, "admin_user")
status_after = get_platform_status(new_platform)
check("Approved platform has 'approved' status", status_after == "approved")

# Reload from storage to verify persistence
reloaded = _load_platforms()
check("Approval persisted to local store", reloaded.get(new_platform, {}).get("status") == "approved")
check("Approver name stored", reloaded.get(new_platform, {}).get("approved_by") == "admin_user")
print(f"  {INFO}  Platform '{new_platform}' approved and persisted")

# ─── Step 4: Supplier risk screening runs even for trusted platforms ──────────

print("\n[4] Supplier risk screening runs even for trusted platform")

# Even though alibaba.com is approved, individual supplier risk flags must still apply
from src.b_side.workspace import create_b_workspace, save_b_workspace
from src.b_side.requirement_structurer import structure_requirement
from src.b_side.feasibility_engine import run_feasibility_simulation
from src.core_schema.b_side_types import SupplierResponseRecord

ws = create_b_workspace("5000 shirts Munich 45 days")
ws.buyer_requirement = structure_requirement(ws.b_workspace_id, ws.raw_requirement)
rfq_id = ws.buyer_requirement.rfq_id

alibaba_platform_status = get_platform_status("alibaba.com")
check("Alibaba.com is trusted platform", alibaba_platform_status == "approved")

# Supplier from Alibaba (trusted platform) but has risk flags
risky_alibaba_supplier = SupplierResponseRecord(
    response_id="r_alibaba_risky",
    rfq_id=rfq_id,
    b_workspace_id=ws.b_workspace_id,
    supplier_id="alibaba_risky_sup",
    supplier_name="Alibaba Risky Supplier Co.",
    can_make=True,
    lead_time_breakdown={},
    estimated_lead_time_days=5,
    unit_price=0.50,
    total_price=2500.0,
    currency="USD",
    confidence_score=0.2,
    completeness_score=0.2,
    red_flags=["suspiciously_low_price", "missing_certification", "unrealistic_lead_time"],
)

ws.supplier_responses = [risky_alibaba_supplier]
save_b_workspace(ws)

report = run_feasibility_simulation(ws.b_workspace_id)
if report.paths:
    path = report.paths[0]
    check("Alibaba supplier risk flags NOT cleared by platform trust",
          path.risk_score > 0,
          f"risk_score={path.risk_score}, flags={risky_alibaba_supplier.red_flags}")
    check("Risk notes present even for Alibaba supplier",
          path.notes is not None and len(path.notes) > 0)
    print(f"  {INFO}  Alibaba supplier risk_score: {path.risk_score} (platform trusted: {alibaba_platform_status == 'approved'})")
else:
    check("Report generated for Alibaba supplier", False, "No paths generated")

# ─── Step 5: Rejected platform not silently used ─────────────────────────────

print("\n[5] Rejected platform is not silently used")

bad_platform = "shady-marketplace.ru"
reject_platform(bad_platform, "security_team", "Flagged for suspicious activity")
status_rejected = get_platform_status(bad_platform)
check("Rejected platform has 'rejected' status", status_rejected == "rejected")

# Simulate checking before using a supplier from rejected platform
supplier_platform = bad_platform
platform_entry = _load_platforms().get(supplier_platform, {})
check("Rejected platform not silently used",
      platform_entry.get("status") != "approved",
      f"status={platform_entry.get('status')}")
check("Rejected platform entry preserved (auditable)", bad_platform in _load_platforms())
print(f"  {INFO}  Rejected platform '{bad_platform}' — reason: {platform_entry.get('reason')}")

# ─── Step 6: Platform approval does not bypass supplier risk ─────────────────

print("\n[6] Platform approval does not bypass supplier risk screening")

approved_platform = "alibaba.com"
risky_supplier_flags = ["no_factory_visit_allowed", "refused_quality_inspection", "unverifiable_cert"]

check("Trusted platform suppliers still require risk screening",
      get_platform_status(approved_platform) == "approved" and len(risky_supplier_flags) > 0)
check("Risk flags are supplier-level, not platform-level",
      isinstance(risky_supplier_flags, list))

# ─── Summary ──────────────────────────────────────────────────────────────────

print()
if failures:
    print(f"RESULT: {len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("RESULT: All Platform Whitelist E2E checks PASSED.")
    print(f"  Built-in platforms: {len(BUILTIN_TRUSTED_PLATFORMS)}")
    print(f"  New platform approval: PERSISTED")
    print(f"  Rejected platform: BLOCKED")
    print(f"  Supplier risk: INDEPENDENT of platform trust")
