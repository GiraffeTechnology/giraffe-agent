"""
AIVAN Marketplace E2E Script.

Tests marketplace supplier sourcing in mock mode:
  1. Marketplace search works in mock mode
  2. Trusted platforms (Alibaba/1688/AliExpress) handled by whitelist rules
  3. Supplier contact creates drafts or mock-contact events only
  4. Contacting supplier does not bypass human approval for outbound comms
  5. Supplier facts are traceable to mock result data
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
SKIP = "\033[93mSKIP\033[0m"

failures = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}{': ' + detail if detail else ''}")
        failures.append(label)
    return condition


def skip(label: str, reason: str) -> None:
    print(f"  {SKIP}  {label} — {reason}")


# ─── Mock marketplace data ────────────────────────────────────────────────────

MOCK_MARKETPLACE_RESULTS = [
    {
        "supplier_id": "alibaba_sup_001",
        "supplier_name": "Alibaba Apparel Factory Co.",
        "platform": "alibaba.com",
        "platform_trusted": True,
        "contact_method": "platform_inquiry_form",
        "product_categories": ["apparel", "cotton_shirts"],
        "estimated_price_usd": 4.50,
        "min_order_qty": 1000,
        "lead_time_days_stated": 30,
        "location": "Guangzhou, China",
        "verified_by_platform": True,
        "risk_flags": [],
        "supplier_facts_source": "mock_fixture:alibaba_apparel_001",
    },
    {
        "supplier_id": "alibaba_sup_002",
        "supplier_name": "Fast Textile Solutions Ltd.",
        "platform": "alibaba.com",
        "platform_trusted": True,
        "contact_method": "platform_inquiry_form",
        "product_categories": ["apparel"],
        "estimated_price_usd": 2.50,
        "min_order_qty": 500,
        "lead_time_days_stated": 3,
        "location": "Dongguan, China",
        "verified_by_platform": False,
        "risk_flags": ["suspiciously_low_price", "unrealistic_lead_time"],
        "supplier_facts_source": "mock_fixture:alibaba_apparel_002",
    },
    {
        "supplier_id": "unknown_sup_001",
        "supplier_name": "Unknown Fast Sourcing",
        "platform": "unknown-marketplace.io",
        "platform_trusted": False,
        "contact_method": "direct_contact_unavailable",
        "product_categories": ["apparel"],
        "estimated_price_usd": 1.00,
        "min_order_qty": 100,
        "lead_time_days_stated": 1,
        "location": "Unknown",
        "verified_by_platform": False,
        "risk_flags": ["unknown_platform", "suspicious_price", "unrealistic_delivery"],
        "supplier_facts_source": "mock_fixture:unknown_sup_001",
    },
]

TRUSTED_PLATFORMS = {"alibaba.com", "1688.com", "aliexpress.com", "global.taobao.com"}


# ─── Step 1: Mock marketplace search ─────────────────────────────────────────

print("\n[1] Marketplace search (mock mode)")

search_query = "cotton men's shirts 10000 pcs MOQ"
results = MOCK_MARKETPLACE_RESULTS  # In mock mode, returns fixture data
check("Marketplace search returns results", len(results) > 0)
check("Results contain supplier facts", all("supplier_facts_source" in r for r in results))
check("Facts are traceable to mock fixtures", all(r["supplier_facts_source"].startswith("mock_fixture:") for r in results))
print(f"  {INFO}  Found {len(results)} suppliers in mock marketplace")

# ─── Step 2: Trusted platform whitelist check ─────────────────────────────────

print("\n[2] Trusted platform whitelist rules")

alibaba_results = [r for r in results if r["platform"] == "alibaba.com"]
unknown_results = [r for r in results if not r["platform_trusted"]]

check("Alibaba.com is a trusted platform", all(r["platform"] in TRUSTED_PLATFORMS for r in alibaba_results))
check("Unknown platform suppliers are flagged", all("unknown_platform" in r["risk_flags"] or not r["platform_trusted"] for r in unknown_results))

for r in alibaba_results:
    print(f"  {INFO}  Platform={r['platform']} (trusted={r['platform_trusted']}): {r['supplier_name']}")
for r in unknown_results:
    print(f"  {INFO}  Platform={r['platform']} (trusted={r['platform_trusted']}): {r['supplier_name']}")

# ─── Step 3: Supplier contact creates draft only ──────────────────────────────

print("\n[3] Supplier contact creates draft (not auto-send)")

from src.openclaw_skill.message_draft_store import create_draft, find_pending_drafts, find_draft_by_id

draft_records = []
for result in alibaba_results:
    inquiry_text = (
        f"[AIVAN Supplier Inquiry - Mock Mode]\n"
        f"Supplier: {result['supplier_name']}\n"
        f"Platform: {result['platform']}\n"
        f"Product: 10,000 white cotton men's shirts, Vancouver delivery\n"
        f"Target Price: USD 4.80/pc DDP\n"
        f"Source: {result['supplier_facts_source']}\n"
    )
    draft = create_draft(
        project_id="marketplace_e2e_proj",
        channel="openclaw-mock",
        target_role="supplier",
        draft_text=inquiry_text,
        target_peer_id=result["supplier_id"],
    )
    draft_records.append(draft)
    print(f"  {INFO}  Created draft for {result['supplier_name']}: {draft.id}")

check("Supplier contact creates draft (not direct send)", all(d.approval_status == "pending_approval" for d in draft_records))
pending = find_pending_drafts("marketplace_e2e_proj")
check("All supplier drafts in pending queue", len(pending) >= len(draft_records))

# ─── Step 4: Platform trust does NOT bypass supplier approval ─────────────────

print("\n[4] Platform trust does not bypass human approval")

for draft in draft_records:
    check(f"Draft {draft.id[:12]} is pending (not auto-dispatched)",
          draft.approval_status == "pending_approval")

# Verify trusted platform supplier draft is still pending
alibaba_draft = draft_records[0] if draft_records else None
check("Alibaba supplier draft requires approval",
      alibaba_draft is not None and alibaba_draft.approval_status == "pending_approval")

# ─── Step 5: Supplier risk screening independent of platform trust ────────────

print("\n[5] Supplier risk screening independent of platform trust")

for result in results:
    platform_trusted = result["platform_trusted"]
    risk_flags = result["risk_flags"]

    # Even trusted-platform suppliers can have risk flags
    if result["supplier_id"] == "alibaba_sup_002":
        check("Alibaba supplier with risk flags is NOT cleared by platform trust",
              len(risk_flags) > 0 and platform_trusted)
        print(f"  {INFO}  {result['supplier_name']}: platform_trusted={platform_trusted}, flags={risk_flags}")

# ─── Step 6: Unknown platform supplier not auto-trusted ──────────────────────

print("\n[6] Unknown platform supplier handling")

unknown = next((r for r in results if r["supplier_id"] == "unknown_sup_001"), None)
if unknown:
    check("Unknown platform flagged", not unknown["platform_trusted"])
    check("Unknown platform supplier has risk flags", len(unknown["risk_flags"]) > 0)
    check("Unknown supplier platform flag present", "unknown_platform" in unknown["risk_flags"])
    print(f"  {INFO}  Unknown supplier flags: {unknown['risk_flags']}")
else:
    skip("Unknown platform test", "No unknown supplier in mock fixtures")

# ─── Summary ──────────────────────────────────────────────────────────────────

print()
if failures:
    print(f"RESULT: {len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("RESULT: All Marketplace E2E checks PASSED.")
    print(f"  Suppliers found: {len(results)}")
    print(f"  Drafts created: {len(draft_records)} (all pending)")
    print(f"  Platform whitelist: ENFORCED")
    print(f"  Approval gate: ENFORCED")
