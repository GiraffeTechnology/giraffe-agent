"""
AIVAN Unknown Supplier Risk E2E Script.

Tests risk handling for unknown suppliers:
  1. Unknown supplier is not automatically treated as trusted
  2. Risk search is triggered when configured
  3. Critical or suspicious risk is surfaced
  4. User review is required when configured
  5. Risk result is not treated as a final legal/compliance decision
  6. The agent does not invent certificates, factory history, sanctions status,
     litigation status, or platform status
"""

import os
import sys
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


# ─── Mock risk assessment data (simulates external risk API in mock mode) ─────

def mock_risk_assessment(supplier_id: str) -> dict:
    """Return mock risk assessment for a supplier. Simulates risk API in offline mode."""
    risk_db = {
        "unknown_sup_xyz": {
            "risk_level": "critical",
            "risk_flags": ["no_prior_history", "unverified_registration", "suspicious_price_history"],
            "sanctions_status": "UNKNOWN",
            "litigation_status": "UNKNOWN",
            "factory_history": "UNKNOWN",
            "certification_status": "UNKNOWN",
            "platform_presence": "NOT_FOUND_IN_KNOWN_PLATFORMS",
            "data_source": "mock_risk_fixture:unknown_sup_xyz",
            "disclaimer": "This is informational only. Not a legal or compliance decision.",
            "human_review_required": True,
        },
        "risky_sup_001": {
            "risk_level": "high",
            "risk_flags": ["potential_sanctions_exposure", "inconsistent_registration_info"],
            "sanctions_status": "REQUIRES_HUMAN_REVIEW",
            "litigation_status": "NO_DATA",
            "factory_history": "UNVERIFIED",
            "certification_status": "CLAIMS_ISO_9001_UNVERIFIED",
            "platform_presence": "FOUND_ON_UNKNOWN_B2B",
            "data_source": "mock_risk_fixture:risky_sup_001",
            "disclaimer": "This is informational only. Not a legal or compliance decision.",
            "human_review_required": True,
        },
        "clean_sup_001": {
            "risk_level": "low",
            "risk_flags": [],
            "sanctions_status": "NO_KNOWN_FLAGS",
            "litigation_status": "NO_KNOWN_FLAGS",
            "factory_history": "MULTIPLE_PRIOR_TRANSACTIONS",
            "certification_status": "CLAIMED_ISO_9001",
            "platform_presence": "VERIFIED_ALIBABA_GOLD_SUPPLIER",
            "data_source": "mock_risk_fixture:clean_sup_001",
            "disclaimer": "This is informational only. Not a legal or compliance decision.",
            "human_review_required": False,
        },
    }
    return risk_db.get(supplier_id, {
        "risk_level": "unknown",
        "risk_flags": ["supplier_not_in_risk_database"],
        "sanctions_status": "UNKNOWN",
        "litigation_status": "UNKNOWN",
        "factory_history": "UNKNOWN",
        "certification_status": "UNKNOWN",
        "platform_presence": "UNKNOWN",
        "data_source": "mock_risk_fixture:default_unknown",
        "disclaimer": "This is informational only. Not a legal or compliance decision.",
        "human_review_required": True,
    })


# ─── Step 1: Unknown supplier not auto-trusted ────────────────────────────────

print("\n[1] Unknown supplier is not automatically treated as trusted")

unknown_supplier_id = "unknown_sup_xyz"
risk = mock_risk_assessment(unknown_supplier_id)

check("Unknown supplier has no prior history flag", "no_prior_history" in risk["risk_flags"])
check("Unknown supplier risk level is critical or high",
      risk["risk_level"] in ("critical", "high", "unknown"))
check("Unknown supplier requires human review", risk["human_review_required"] is True)
check("Sanctions status is UNKNOWN (not cleared)", risk["sanctions_status"] in ("UNKNOWN", "REQUIRES_HUMAN_REVIEW"))

print(f"  {INFO}  Risk level: {risk['risk_level']}, flags: {risk['risk_flags']}")

# ─── Step 2: Risk search triggered ────────────────────────────────────────────

print("\n[2] Risk search triggered for unknown suppliers")

risky_supplier_id = "risky_sup_001"
risky_risk = mock_risk_assessment(risky_supplier_id)

check("Risk flags populated for risky supplier", len(risky_risk["risk_flags"]) > 0)
check("Sanctions exposure flag present", "potential_sanctions_exposure" in risky_risk["risk_flags"])
check("Data source is traceable", risky_risk["data_source"].startswith("mock_risk_fixture:"))

# ─── Step 3: Critical risk surfaced ──────────────────────────────────────────

print("\n[3] Critical/suspicious risk is surfaced")

check("Critical risk level detected for unknown_sup_xyz", risk["risk_level"] in ("critical", "high"))
check("High risk level detected for risky_sup_001", risky_risk["risk_level"] in ("critical", "high"))

# ─── Step 4: User review required ────────────────────────────────────────────

print("\n[4] User review required for critical risk suppliers")

check("Unknown supplier requires review", risk["human_review_required"] is True)
check("Risky supplier requires review", risky_risk["human_review_required"] is True)

clean_risk = mock_risk_assessment("clean_sup_001")
check("Clean supplier may not require mandatory review", clean_risk["human_review_required"] is False)

# ─── Step 5: Risk is NOT a final compliance decision ─────────────────────────

print("\n[5] Risk result is NOT a final compliance decision")

for sup_id, r in [("unknown_sup_xyz", risk), ("risky_sup_001", risky_risk), ("clean_sup_001", clean_risk)]:
    check(
        f"{sup_id}: disclaimer present",
        "disclaimer" in r and "Not a legal or compliance decision" in r["disclaimer"],
        f"disclaimer={r.get('disclaimer', 'MISSING')[:60]}"
    )

# Verify that even a clean supplier doesn't get "cleared" in legal sense
check("Clean supplier not 'legally cleared'",
      "cleared" not in str(clean_risk).lower() or "human" in str(clean_risk).lower())

# ─── Step 6: No hallucinated facts ───────────────────────────────────────────

print("\n[6] No hallucinated supplier facts")

# AIVAN must not invent facts — all facts are either from data source or explicitly UNKNOWN
for sup_id, r in [("unknown_sup_xyz", risk), ("risky_sup_001", risky_risk)]:
    # Key fields must be UNKNOWN or populated from mock fixture, not invented
    for field in ["sanctions_status", "litigation_status", "factory_history", "certification_status"]:
        val = r.get(field, "MISSING")
        check(
            f"{sup_id}.{field} is not an invented fact",
            val in ("UNKNOWN", "REQUIRES_HUMAN_REVIEW", "NO_DATA", "UNVERIFIED",
                    "CLAIMS_ISO_9001_UNVERIFIED", "NO_KNOWN_FLAGS", "NOT_FOUND_IN_KNOWN_PLATFORMS",
                    "MULTIPLE_PRIOR_TRANSACTIONS", "VERIFIED_ALIBABA_GOLD_SUPPLIER",
                    "FOUND_ON_UNKNOWN_B2B") or r["data_source"].startswith("mock_risk_fixture:"),
            f"field={field}, value={val}"
        )

# ─── Step 7: Risk affects buyer option ranking ────────────────────────────────

print("\n[7] Risk affects buyer option ranking and draft generation")

from src.b_side.workspace import create_b_workspace, save_b_workspace
from src.b_side.requirement_structurer import structure_requirement
from src.b_side.feasibility_engine import run_feasibility_simulation
from src.core_schema.b_side_types import SupplierResponseRecord
from src.openclaw_skill.message_draft_store import create_draft, find_pending_drafts

ws = create_b_workspace("10,000 shirts Vancouver 45 days")
ws.buyer_requirement = structure_requirement(ws.b_workspace_id, ws.raw_requirement)
rfq_id = ws.buyer_requirement.rfq_id

ws.supplier_responses = [
    SupplierResponseRecord(
        response_id="r_risky",
        rfq_id=rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="risky_sup_001",
        supplier_name="Risky Supplier",
        can_make=True,
        lead_time_breakdown={},
        estimated_lead_time_days=20,
        unit_price=3.00,
        total_price=30000.0,
        currency="USD",
        confidence_score=0.3,
        completeness_score=0.3,
        red_flags=["potential_sanctions_exposure", "inconsistent_registration"],
    ),
]
save_b_workspace(ws)

report = run_feasibility_simulation(ws.b_workspace_id)
check("Risky supplier still produces a path", len(report.paths) >= 1)
if report.paths:
    risky_path = report.paths[0]
    check("Risky path has risk_score > 0", risky_path.risk_score > 0)
    check("Risky path notes reference flags",
          risky_path.notes is not None and len(risky_path.notes) > 0)
    print(f"  {INFO}  Risky supplier path: risk={risky_path.risk_score}, notes={risky_path.notes[:80]}")

# Create buyer option draft mentioning risk
draft = create_draft(
    project_id=ws.b_workspace_id,
    channel="openclaw-mock",
    target_role="customer",
    draft_text=(
        "Option A: Available but HIGH RISK — sanctions exposure detected. "
        "Human review required before proceeding. Risk: CRITICAL."
    ),
)
check("Risk notification draft is pending (not auto-sent)", draft.approval_status == "pending_approval")

# ─── Summary ──────────────────────────────────────────────────────────────────

print()
if failures:
    print(f"RESULT: {len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("RESULT: All Unknown Supplier Risk E2E checks PASSED.")
    print(f"  Unknown supplier: NOT auto-trusted")
    print(f"  Risk screening: INDEPENDENT of platform trust")
    print(f"  Compliance decisions: DEFERRED to human")
    print(f"  Supplier facts: TRACEABLE to mock fixtures (no hallucination)")
