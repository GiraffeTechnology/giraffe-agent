#!/usr/bin/env python3
"""
B-side integration test suite — 33 scenario-based tests.

Tests the full B-side AI Buyer flow end-to-end without requiring
a live database or LLM. All storage is redirected to a temporary
directory via monkeypatching.

Run from apps/bside/:
    python run_tests.py
"""

import sys
import os
import uuid
import json
import traceback
from pathlib import Path
from tempfile import mkdtemp
import shutil
from unittest.mock import patch

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PASS = "PASS"
FAIL = "FAIL"

results = []
_temp_dir = None


def setup():
    global _temp_dir
    _temp_dir = Path(mkdtemp())


def teardown():
    if _temp_dir and _temp_dir.exists():
        shutil.rmtree(_temp_dir, ignore_errors=True)


def _temp(subdir):
    p = _temp_dir / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


def run_test(name, fn):
    try:
        fn()
        results.append((PASS, name))
        print(f"  PASS  {name}")
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  FAIL  {name}: {e}")


# ─── Test Helpers ─────────────────────────────────────────────────────────────

def _patch_dirs():
    import src.b_side.workspace as bw_mod
    import src.m_side.m_event_logger as mel_mod
    bw_mod._DATA_DIR = _temp("bw")
    mel_mod._EVENTS_FILE = _temp_dir / "events.jsonl"


def _make_rfq_id():
    return f"RFQ-{uuid.uuid4().hex[:8].upper()}"


# ─── Scenario 1: Create B-side Workspace ─────────────────────────────────────

def test_01_create_workspace():
    _patch_dirs()
    from src.b_side.workspace import create_b_workspace
    ws = create_b_workspace("100 pcs aluminum CNC bracket for Munich")
    assert ws.b_workspace_id.startswith("bw_")
    assert ws.status == "created"


def test_02_workspace_persisted():
    from src.b_side.workspace import create_b_workspace, get_b_workspace
    ws = create_b_workspace("200 pcs cotton shirt for Berlin")
    loaded = get_b_workspace(ws.b_workspace_id)
    assert loaded.b_workspace_id == ws.b_workspace_id


def test_03_workspace_unique_ids():
    from src.b_side.workspace import create_b_workspace
    ws1 = create_b_workspace("req 1")
    ws2 = create_b_workspace("req 2")
    assert ws1.b_workspace_id != ws2.b_workspace_id


# ─── Scenario 2: Structure Requirement ───────────────────────────────────────

def test_04_structure_cnc_requirement():
    from src.b_side.requirement_structurer import structure_requirement
    req = structure_requirement(
        "bw_test_04",
        "100 pcs aluminum 6061 CNC bracket, tolerance ±0.05 mm, delivery before September 30, to Munich"
    )
    assert req.quantity == 100
    assert req.category == "cnc"
    assert req.confidence_score == 1.0


def test_05_structure_apparel_requirement():
    from src.b_side.requirement_structurer import structure_requirement
    req = structure_requirement(
        "bw_test_05",
        "500 pcs cotton shirt, delivery before October 15, ship to Shanghai"
    )
    assert req.quantity == 500
    assert req.category == "apparel"


def test_06_partial_requirement_detects_missing():
    from src.b_side.requirement_structurer import structure_requirement
    req = structure_requirement("bw_test_06", "some aluminum bracket")
    assert "quantity" in req.missing_fields


def test_07_requirement_rfq_id_generated():
    from src.b_side.requirement_structurer import structure_requirement
    req = structure_requirement("bw_test_07", "100 pcs bracket")
    assert req.rfq_id.startswith("RFQ-")


def test_08_confidence_reflects_completeness():
    from src.b_side.requirement_structurer import structure_requirement
    full = structure_requirement(
        "bw_full",
        "100 pcs aluminum 6061 CNC bracket, delivery before September 30, to Munich"
    )
    partial = structure_requirement("bw_partial", "some bracket")
    assert full.confidence_score > partial.confidence_score


# ─── Scenario 3: Draft Supplier Inquiry ──────────────────────────────────────

def test_09_draft_inquiry_generates_bilingual():
    from src.b_side.workspace import save_b_workspace, _ensure_dir
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.core_schema.b_side_types import BWWorkspace, BuyerRequirement

    _ensure_dir()
    bw_id = "bw_draft09"
    req = BuyerRequirement(rfq_id="RFQ-D09", b_workspace_id=bw_id, raw_text="test", quantity=100)
    ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-D09",
                     raw_requirement="test", buyer_requirement=req)
    save_b_workspace(ws)

    draft = draft_supplier_inquiry(bw_id, ["s1", "s2"])
    assert "Giraffe Agent" in draft.message_text_en
    assert "供应商询盘" in draft.message_text_zh


def test_10_draft_includes_supplier_ids():
    from src.b_side.workspace import save_b_workspace, _ensure_dir
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.core_schema.b_side_types import BWWorkspace, BuyerRequirement

    _ensure_dir()
    bw_id = "bw_draft10"
    req = BuyerRequirement(rfq_id="RFQ-D10", b_workspace_id=bw_id, raw_text="test")
    ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-D10",
                     raw_requirement="test", buyer_requirement=req)
    save_b_workspace(ws)

    draft = draft_supplier_inquiry(bw_id, ["s_a", "s_b", "s_c"])
    assert len(draft.supplier_ids) == 3


def test_11_draft_has_required_fields():
    from src.b_side.workspace import save_b_workspace, _ensure_dir
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.core_schema.b_side_types import BWWorkspace, BuyerRequirement

    _ensure_dir()
    bw_id = "bw_draft11"
    req = BuyerRequirement(rfq_id="RFQ-D11", b_workspace_id=bw_id, raw_text="test")
    ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-D11",
                     raw_requirement="test", buyer_requirement=req)
    save_b_workspace(ws)

    draft = draft_supplier_inquiry(bw_id, ["s1"])
    assert "can_make" in draft.required_fields
    assert "lead_time_days" in draft.required_fields


def test_12_draft_raises_without_requirement():
    from src.b_side.workspace import save_b_workspace, _ensure_dir
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.core_schema.b_side_types import BWWorkspace

    _ensure_dir()
    bw_id = "bw_draft12"
    ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-D12", raw_requirement="test")
    save_b_workspace(ws)

    raised = False
    try:
        draft_supplier_inquiry(bw_id, ["s1"])
    except ValueError:
        raised = True
    assert raised, "Expected ValueError"


# ─── Scenario 4: Intake Supplier Responses ───────────────────────────────────

def test_13_intake_one_response():
    from src.b_side.workspace import create_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs aluminum bracket")
    resp = SupplierResponseRecord(
        response_id="RSP-13",
        rfq_id=ws.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_13",
        supplier_name="Test 13",
        can_make=True,
    )
    updated = intake_supplier_response(ws.b_workspace_id, resp)
    assert len(updated.supplier_responses) == 1


def test_14_intake_multiple_suppliers():
    from src.b_side.workspace import create_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("200 pcs cotton shirt")
    for i in range(3):
        resp = SupplierResponseRecord(
            response_id=f"RSP-14{i}",
            rfq_id=ws.rfq_id,
            b_workspace_id=ws.b_workspace_id,
            supplier_id=f"sup_14{i}",
            supplier_name=f"Supplier 14{i}",
            can_make=True,
        )
        intake_supplier_response(ws.b_workspace_id, resp)

    from src.b_side.workspace import get_b_workspace
    loaded = get_b_workspace(ws.b_workspace_id)
    assert len(loaded.supplier_responses) == 3


def test_15_intake_deduplicates_same_supplier():
    from src.b_side.workspace import create_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs test")
    for i in range(2):
        resp = SupplierResponseRecord(
            response_id=f"RSP-15-{i}",
            rfq_id=ws.rfq_id,
            b_workspace_id=ws.b_workspace_id,
            supplier_id="sup_dup_15",
            supplier_name="Dup Supplier",
            can_make=True,
        )
        intake_supplier_response(ws.b_workspace_id, resp)

    from src.b_side.workspace import get_b_workspace
    loaded = get_b_workspace(ws.b_workspace_id)
    assert len(loaded.supplier_responses) == 1


def test_16_intake_status_becomes_collecting():
    from src.b_side.workspace import create_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs test")
    assert ws.status == "created"

    resp = SupplierResponseRecord(
        response_id="RSP-16",
        rfq_id=ws.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_16",
        supplier_name="S16",
        can_make=True,
    )
    updated = intake_supplier_response(ws.b_workspace_id, resp)
    assert updated.status == "collecting_responses"


# ─── Scenario 5: Run Feasibility Simulation ──────────────────────────────────

def test_17_feasibility_ranks_suppliers():
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.b_side.requirement_structurer import structure_requirement
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs CNC bracket")
    req = structure_requirement(ws.b_workspace_id, "100 pcs aluminum 6061 CNC bracket")
    ws.buyer_requirement = req
    save_b_workspace(ws)

    for i, (lt, conf) in enumerate([(10, 0.95), (30, 0.7), (60, 0.5)]):
        resp = SupplierResponseRecord(
            response_id=f"RSP-17{i}",
            rfq_id=req.rfq_id,
            b_workspace_id=ws.b_workspace_id,
            supplier_id=f"sup_17{i}",
            supplier_name=f"Supplier {i}",
            can_make=True,
            estimated_lead_time_days=lt,
            confidence_score=conf,
        )
        intake_supplier_response(ws.b_workspace_id, resp)

    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 3
    assert report.paths[0].rank == 1


def test_18_feasibility_excludes_cannot_make():
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.b_side.requirement_structurer import structure_requirement
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs bracket")
    req = structure_requirement(ws.b_workspace_id, "100 pcs aluminum bracket")
    ws.buyer_requirement = req
    save_b_workspace(ws)

    r_can = SupplierResponseRecord(
        response_id="RSP-18A",
        rfq_id=req.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_can",
        supplier_name="Can Make",
        can_make=True,
        confidence_score=0.8,
    )
    r_cannot = SupplierResponseRecord(
        response_id="RSP-18B",
        rfq_id=req.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_cannot",
        supplier_name="Cannot Make",
        can_make=False,
    )
    intake_supplier_response(ws.b_workspace_id, r_can)
    intake_supplier_response(ws.b_workspace_id, r_cannot)

    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 1
    assert report.paths[0].supplier_id == "sup_can"


def test_19_feasibility_empty_when_no_can_make():
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.b_side.requirement_structurer import structure_requirement
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("50 pcs test")
    req = structure_requirement(ws.b_workspace_id, "50 pcs test bracket")
    ws.buyer_requirement = req
    save_b_workspace(ws)

    r = SupplierResponseRecord(
        response_id="RSP-19",
        rfq_id=req.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_19",
        supplier_name="No",
        can_make=False,
    )
    intake_supplier_response(ws.b_workspace_id, r)
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 0


def test_20_feasibility_workspace_status_updated():
    from src.b_side.workspace import create_b_workspace, save_b_workspace, get_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.b_side.requirement_structurer import structure_requirement
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs bracket")
    req = structure_requirement(ws.b_workspace_id, "100 pcs aluminum bracket")
    ws.buyer_requirement = req
    save_b_workspace(ws)

    r = SupplierResponseRecord(
        response_id="RSP-20",
        rfq_id=req.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_20",
        supplier_name="S20",
        can_make=True,
        confidence_score=0.85,
    )
    intake_supplier_response(ws.b_workspace_id, r)
    run_feasibility_simulation(ws.b_workspace_id)

    loaded = get_b_workspace(ws.b_workspace_id)
    assert loaded.status == "feasibility_complete"


# ─── Scenario 6: Full B-side Flow ────────────────────────────────────────────

def test_21_full_bside_flow():
    from src.b_side.workspace import create_b_workspace, save_b_workspace, get_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.core_schema.b_side_types import SupplierResponseRecord

    # Step 1: Create workspace
    ws = create_b_workspace("100 pcs aluminum 6061 CNC bracket, to Munich")

    # Step 2: Structure requirement
    req = structure_requirement(ws.b_workspace_id, ws.raw_requirement)
    ws.buyer_requirement = req
    save_b_workspace(ws)

    # Step 3: Intake two supplier responses
    for i, lt in enumerate([20, 35]):
        resp = SupplierResponseRecord(
            response_id=f"RSP-21-{i}",
            rfq_id=req.rfq_id,
            b_workspace_id=ws.b_workspace_id,
            supplier_id=f"sup_21{i}",
            supplier_name=f"Supplier 21{i}",
            can_make=True,
            estimated_lead_time_days=lt,
            confidence_score=0.9 - i * 0.1,
            unit_price=10.0 + i,
            currency="USD",
        )
        intake_supplier_response(ws.b_workspace_id, resp)

    # Step 4: Run feasibility
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 2
    assert report.paths[0].rank == 1


def test_22_full_flow_best_path_is_rank_1():
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("200 pcs cotton shirt, to Beijing")
    req = structure_requirement(ws.b_workspace_id, ws.raw_requirement)
    ws.buyer_requirement = req
    save_b_workspace(ws)

    # Best supplier (fast, high confidence)
    best = SupplierResponseRecord(
        response_id="RSP-22A",
        rfq_id=req.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_best",
        supplier_name="Best Supplier",
        can_make=True,
        estimated_lead_time_days=15,
        confidence_score=0.95,
    )
    # Worse supplier
    worse = SupplierResponseRecord(
        response_id="RSP-22B",
        rfq_id=req.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_worse",
        supplier_name="Worse Supplier",
        can_make=True,
        estimated_lead_time_days=60,
        confidence_score=0.5,
    )
    intake_supplier_response(ws.b_workspace_id, best)
    intake_supplier_response(ws.b_workspace_id, worse)

    report = run_feasibility_simulation(ws.b_workspace_id)
    assert report.paths[0].supplier_id == "sup_best"


# ─── Scenario 7: Role Resolution ─────────────────────────────────────────────

def test_23_original_buyer_role():
    from src.actors.role_resolver import resolve_role_context
    rc = resolve_role_context(
        project_id="PROJ-23",
        actor_id="actor_buyer",
        original_buyer_actor_id="actor_buyer",
        main_supplier_actor_id="actor_mfg",
    )
    assert rc.role == "ORIGINAL_BUYER"
    assert rc.can_create_upstream_inquiry is False


def test_24_main_m_side_role():
    from src.actors.role_resolver import resolve_role_context
    rc = resolve_role_context(
        project_id="PROJ-24",
        actor_id="actor_mfg",
        original_buyer_actor_id="actor_buyer",
        main_supplier_actor_id="actor_mfg",
    )
    assert rc.role == "MAIN_M_SIDE"
    assert rc.can_create_upstream_inquiry is True


def test_25_upstream_b_side_role():
    from src.actors.role_resolver import resolve_role_context
    rc = resolve_role_context(
        project_id="PROJ-25",
        actor_id="actor_mfg",
        original_buyer_actor_id="actor_buyer",
        main_supplier_actor_id="actor_mfg",
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
    )
    assert rc.role == "UPSTREAM_B_SIDE"


def test_26_upstream_m_side_role():
    from src.actors.role_resolver import resolve_role_context
    rc = resolve_role_context(
        project_id="PROJ-26",
        actor_id="actor_fabric",
        original_buyer_actor_id="actor_buyer",
        main_supplier_actor_id="actor_mfg",
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
    )
    assert rc.role == "UPSTREAM_M_SIDE"


# ─── Scenario 8: Edge Cases ───────────────────────────────────────────────────

def test_27_workspace_not_found_raises():
    from src.b_side.workspace import get_b_workspace
    try:
        get_b_workspace("bw_definitely_not_here_xyz")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_28_requirement_rfq_id_unique():
    from src.b_side.requirement_structurer import structure_requirement
    req1 = structure_requirement("bw_28a", "100 pcs aluminum bracket")
    req2 = structure_requirement("bw_28b", "100 pcs aluminum bracket")
    assert req1.rfq_id != req2.rfq_id


def test_29_update_workspace_status():
    from src.b_side.workspace import create_b_workspace, update_b_workspace_status
    ws = create_b_workspace("test")
    updated = update_b_workspace_status(ws.b_workspace_id, "inquiry_drafted")
    assert updated.status == "inquiry_drafted"


def test_30_response_scoring_positive():
    from src.b_side.feasibility_engine import _score_response
    from src.core_schema.b_side_types import SupplierResponseRecord
    r = SupplierResponseRecord(
        response_id="RSP-30",
        rfq_id="RFQ-30",
        b_workspace_id="bw_30",
        supplier_id="s30",
        supplier_name="S30",
        confidence_score=0.9,
        estimated_lead_time_days=20,
    )
    assert _score_response(r) > 0


def test_31_requirement_confidence_one_when_all_fields():
    from src.b_side.requirement_structurer import structure_requirement
    req = structure_requirement(
        "bw_31",
        "100 pcs aluminum 6061, delivery before September 30, to Munich"
    )
    assert req.confidence_score == 1.0


def test_32_feasibility_paths_have_unique_ids():
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.supplier_response_intake import intake_supplier_response
    from src.b_side.feasibility_engine import run_feasibility_simulation
    from src.b_side.requirement_structurer import structure_requirement
    from src.core_schema.b_side_types import SupplierResponseRecord

    ws = create_b_workspace("100 pcs bracket")
    req = structure_requirement(ws.b_workspace_id, "100 pcs aluminum bracket")
    ws.buyer_requirement = req
    save_b_workspace(ws)

    for i in range(4):
        resp = SupplierResponseRecord(
            response_id=f"RSP-32{i}",
            rfq_id=req.rfq_id,
            b_workspace_id=ws.b_workspace_id,
            supplier_id=f"s32{i}",
            supplier_name=f"S{i}",
            can_make=True,
            confidence_score=0.7,
        )
        intake_supplier_response(ws.b_workspace_id, resp)

    report = run_feasibility_simulation(ws.b_workspace_id)
    path_ids = [p.path_id for p in report.paths]
    assert len(set(path_ids)) == len(path_ids)


def test_33_workspace_raw_requirement_preserved():
    from src.b_side.workspace import create_b_workspace, get_b_workspace
    raw = "500 pcs premium cotton t-shirt for export to London"
    ws = create_b_workspace(raw)
    loaded = get_b_workspace(ws.b_workspace_id)
    assert loaded.raw_requirement == raw


# ─── Main Runner ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nGiraffe Agent B-side Integration Tests")
    print("=" * 50)

    setup()
    try:
        tests = [
            ("01 Create B-side Workspace", test_01_create_workspace),
            ("02 Workspace Persisted", test_02_workspace_persisted),
            ("03 Workspace Unique IDs", test_03_workspace_unique_ids),
            ("04 Structure CNC Requirement", test_04_structure_cnc_requirement),
            ("05 Structure Apparel Requirement", test_05_structure_apparel_requirement),
            ("06 Partial Requirement Detects Missing", test_06_partial_requirement_detects_missing),
            ("07 Requirement RFQ ID Generated", test_07_requirement_rfq_id_generated),
            ("08 Confidence Reflects Completeness", test_08_confidence_reflects_completeness),
            ("09 Draft Inquiry Bilingual", test_09_draft_inquiry_generates_bilingual),
            ("10 Draft Includes Supplier IDs", test_10_draft_includes_supplier_ids),
            ("11 Draft Has Required Fields", test_11_draft_has_required_fields),
            ("12 Draft Raises Without Requirement", test_12_draft_raises_without_requirement),
            ("13 Intake One Response", test_13_intake_one_response),
            ("14 Intake Multiple Suppliers", test_14_intake_multiple_suppliers),
            ("15 Intake Deduplicates", test_15_intake_deduplicates_same_supplier),
            ("16 Intake Status Becomes Collecting", test_16_intake_status_becomes_collecting),
            ("17 Feasibility Ranks Suppliers", test_17_feasibility_ranks_suppliers),
            ("18 Feasibility Excludes Cannot Make", test_18_feasibility_excludes_cannot_make),
            ("19 Feasibility Empty No Can Make", test_19_feasibility_empty_when_no_can_make),
            ("20 Feasibility Status Updated", test_20_feasibility_workspace_status_updated),
            ("21 Full B-side Flow", test_21_full_bside_flow),
            ("22 Best Path Is Rank 1", test_22_full_flow_best_path_is_rank_1),
            ("23 Original Buyer Role", test_23_original_buyer_role),
            ("24 Main M-side Role", test_24_main_m_side_role),
            ("25 Upstream B-side Role", test_25_upstream_b_side_role),
            ("26 Upstream M-side Role", test_26_upstream_m_side_role),
            ("27 Workspace Not Found Raises", test_27_workspace_not_found_raises),
            ("28 Requirement RFQ ID Unique", test_28_requirement_rfq_id_unique),
            ("29 Update Workspace Status", test_29_update_workspace_status),
            ("30 Response Scoring Positive", test_30_response_scoring_positive),
            ("31 Full Confidence With All Fields", test_31_requirement_confidence_one_when_all_fields),
            ("32 Feasibility Path IDs Unique", test_32_feasibility_paths_have_unique_ids),
            ("33 Workspace Raw Requirement Preserved", test_33_workspace_raw_requirement_preserved),
        ]

        for name, fn in tests:
            run_test(name, fn)

    finally:
        teardown()

    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    total = len(results)

    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} passed")
    if failed:
        print(f"FAILED ({failed}):")
        for r in results:
            if r[0] == FAIL:
                print(f"  - {r[1]}: {r[2]}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
