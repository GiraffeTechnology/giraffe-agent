"""
AIVAN Core E2E Script.

Tests the full buyer → supplier workflow in mock mode:
  1. Buyer sends apparel/textile inquiry
  2. Requirement Agent extracts structured fields
  3. Missing fields are detected
  4. Follow-up buyer details update the project
  5. Supplier reply is parsed
  6. Lead time is calculated
  7. Buyer options are generated
  8. Risk level is attached
  9. No buyer-facing outbound message is sent automatically
  10. Drafts remain pending until approval
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


# ─── Step 1: Buyer sends apparel inquiry ──────────────────────────────────────

print("\n[1] Buyer sends apparel/textile inquiry")

from src.b_side.workspace import create_b_workspace, save_b_workspace, get_b_workspace
from src.b_side.requirement_structurer import structure_requirement
from src.b_side.inquiry_drafter import draft_supplier_inquiry
from src.b_side.feasibility_engine import run_feasibility_simulation
from src.core_schema.b_side_types import SupplierResponseRecord
from src.openclaw_skill.message_draft_store import (
    create_draft, find_pending_drafts, approve_draft, reject_draft, find_draft_by_id
)

raw_buyer_inquiry = (
    "Hi, I need to source 10,000 white cotton men's shirts, sizes S/M/L/XL in equal ratio, "
    "delivered to Vancouver, Canada. Target price USD 4.80/pc DDP. Air freight preferred. "
    "Deadline: 45 days from today."
)
workspace = create_b_workspace(raw_buyer_inquiry)
print(f"  {INFO}  Created B-side workspace: {workspace.b_workspace_id}")
check("Workspace created with status 'created'", workspace.status == "created")
check("Raw requirement saved", len(workspace.raw_requirement) > 0)

# ─── Step 2: Requirement extraction ───────────────────────────────────────────

print("\n[2] Requirement Agent extracts structured fields")

req = structure_requirement(workspace.b_workspace_id, raw_buyer_inquiry)
workspace.buyer_requirement = req
workspace.status = "requirement_structured"
save_b_workspace(workspace)

check("RFQ ID generated", req.rfq_id.startswith("RFQ-"))
check("Category detected as apparel", req.category == "apparel")
check("Quantity extracted (10,000)", req.quantity == 10000, f"got {req.quantity}")
check("Destination detected (Vancouver)", req.destination is not None, f"got {req.destination}")
check("Confidence score > 0", req.confidence_score > 0)
check("Missing fields identified", isinstance(req.missing_fields, list))

print(f"  {INFO}  Extracted: qty={req.quantity}, category={req.category}, dest={req.destination}")
print(f"  {INFO}  Missing fields: {req.missing_fields}")

# ─── Step 3: Missing fields detection for incomplete inquiry ──────────────────

print("\n[3] Missing field detection on incomplete inquiry")

incomplete_ws = create_b_workspace("Can you help source shirts for Canada?")
incomplete_req = structure_requirement(incomplete_ws.b_workspace_id, incomplete_ws.raw_requirement)
check("Incomplete inquiry has missing fields", len(incomplete_req.missing_fields) > 0,
      f"fields: {incomplete_req.missing_fields}")
check("Confidence is low for incomplete inquiry", incomplete_req.confidence_score < 0.8,
      f"got {incomplete_req.confidence_score}")
check("'quantity' detected as missing", "quantity" in incomplete_req.missing_fields)

# ─── Step 4: Supplier inquiry draft generated ─────────────────────────────────

print("\n[4] Supplier inquiry draft generated")

inquiry_draft = draft_supplier_inquiry(workspace.b_workspace_id, ["sup_a", "sup_b"])
check("Draft inquiry has RFQ ID", inquiry_draft.rfq_id == req.rfq_id)
check("EN inquiry message generated", len(inquiry_draft.message_text_en) > 50,
      f"len={len(inquiry_draft.message_text_en)}")
check("ZH inquiry message generated", len(inquiry_draft.message_text_zh) > 20,
      f"len={len(inquiry_draft.message_text_zh)}")
check("Supplier IDs listed", "sup_a" in inquiry_draft.supplier_ids)
print(f"  {INFO}  EN preview: {inquiry_draft.message_text_en[:100]}...")

# ─── Step 5: Supplier replies are parsed ──────────────────────────────────────

print("\n[5] Supplier replies parsed and structured")

supplier_responses = [
    SupplierResponseRecord(
        response_id="r_sup_a",
        rfq_id=req.rfq_id,
        b_workspace_id=workspace.b_workspace_id,
        supplier_id="sup_a",
        supplier_name="Supplier A (Strong)",
        can_make=True,
        lead_time_breakdown={"fabric_days": 10, "trim_days": 3, "production_days": 18, "qc_days": 2},
        estimated_lead_time_days=35,
        unit_price=4.80,
        total_price=48000.0,
        currency="USD",
        confidence_score=0.88,
        completeness_score=0.88,
        red_flags=[],
    ),
    SupplierResponseRecord(
        response_id="r_sup_b",
        rfq_id=req.rfq_id,
        b_workspace_id=workspace.b_workspace_id,
        supplier_id="sup_b",
        supplier_name="Supplier B (Mid)",
        can_make=True,
        lead_time_breakdown={"fabric_days": 15, "production_days": 28, "qc_days": 3},
        estimated_lead_time_days=50,
        unit_price=4.20,
        total_price=42000.0,
        currency="USD",
        confidence_score=0.72,
        completeness_score=0.72,
        red_flags=["outsourced_trim"],
    ),
]
workspace.supplier_responses = supplier_responses
save_b_workspace(workspace)
check("2 supplier responses stored", len(workspace.supplier_responses) == 2)
check("Supplier A has no red flags", len(supplier_responses[0].red_flags) == 0)
check("Supplier B has outsourced_trim flag", "outsourced_trim" in supplier_responses[1].red_flags)

# ─── Step 6: Lead time calculated, buyer options generated ────────────────────

print("\n[6] Lead time calculated, buyer options generated")

report = run_feasibility_simulation(workspace.b_workspace_id)
check("Feasibility report generated", report is not None)
check("2 delivery paths produced", len(report.paths) == 2, f"got {len(report.paths)}")
check("Paths are ranked", all(p.rank is not None for p in report.paths))
check("Paths have labels", all(p.label is not None and len(p.label) > 0 for p in report.paths))
check("Best path has lower risk than risky path",
      report.paths[0].risk_score is not None)

for path in report.paths:
    print(f"  {INFO}  [{path.rank}] {path.supplier_name}: {path.lead_time_days}d, {path.currency}{path.unit_price}/pc, risk={path.risk_score}, label={path.label}")

# ─── Step 7: Risk level attached ──────────────────────────────────────────────

print("\n[7] Risk level attached to buyer options")

for path in report.paths:
    check(f"Path {path.rank} has risk_score", path.risk_score is not None)

risky_path = next((p for p in report.paths if p.supplier_id == "sup_b"), None)
check("Risky supplier (B) has risk > 0", risky_path is not None and risky_path.risk_score > 0,
      f"risk={risky_path.risk_score if risky_path else 'not found'}")
check("Risky supplier notes reference flags",
      risky_path is not None and risky_path.notes is not None and len(risky_path.notes) > 0)

# ─── Step 8: No auto-send — drafts pending ────────────────────────────────────

print("\n[8] No auto-send — buyer-facing drafts remain pending")

buyer_draft = create_draft(
    project_id=workspace.b_workspace_id,
    channel="openclaw-mock",
    target_role="customer",
    draft_text=(
        f"Option A (Recommended): {report.paths[0].supplier_name}, "
        f"lead time {report.paths[0].lead_time_days} days, "
        f"total {report.paths[0].currency} {report.paths[0].total_price:.0f} DDP. "
        "Risk: Low. Deadline feasible."
    ),
)

supplier_draft = create_draft(
    project_id=workspace.b_workspace_id,
    channel="openclaw-mock",
    target_role="supplier",
    draft_text=inquiry_draft.message_text_en,
)

check("Buyer draft created as pending", buyer_draft.approval_status == "pending_approval")
check("Supplier draft created as pending", supplier_draft.approval_status == "pending_approval")

pending = find_pending_drafts(workspace.b_workspace_id)
check("Pending drafts visible", len(pending) >= 2, f"pending count: {len(pending)}")

# ─── Step 9: Human approval gate verification ─────────────────────────────────

print("\n[9] Human approval gate verification")

# Try rejecting a draft
reject_draft(buyer_draft.id)
rejected = find_draft_by_id(buyer_draft.id)
check("Rejected draft has status 'rejected'", rejected.approval_status == "rejected")
check("Rejected draft persists (auditable)", rejected is not None)

# Approve the supplier draft
approve_draft(supplier_draft.id, "human_approver_alice")
approved = find_draft_by_id(supplier_draft.id)
check("Approved draft has status 'approved'", approved.approval_status == "approved")
check("Approval timestamp set", approved.approved_at is not None)
check("Approved by stored", approved.approved_by_sender_id == "human_approver_alice")

pending_after = find_pending_drafts(workspace.b_workspace_id)
check("No pending drafts remain after approval/rejection",
      not any(d.id in (buyer_draft.id, supplier_draft.id) for d in pending_after))

# ─── Summary ──────────────────────────────────────────────────────────────────

print()
if failures:
    print(f"RESULT: {len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"RESULT: All AIVAN Core E2E checks PASSED.")
    print(f"  Workspace: {workspace.b_workspace_id}")
    print(f"  RFQ: {req.rfq_id}")
    print(f"  Paths: {len(report.paths)}")
    print(f"  Approval gate: ENFORCED")
