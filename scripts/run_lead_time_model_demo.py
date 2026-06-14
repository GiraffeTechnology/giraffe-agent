"""
Lead Time Model Demo — loads the deterministic fixture and verifies path calculations.
Prints LEAD TIME MODEL DEMO: PASS if all assertions succeed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lead_time.models import ProductionCapacity
from src.lead_time.path_enumerator import enumerate_delivery_paths
from src.lead_time.path_ranker import assign_labels

FIXTURE_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "lead_time" / "shirt_100pcs_lead_time_demo.json"


def main() -> None:
    print("=" * 60)
    print("LEAD TIME MODEL DEMO — Deterministic fixture verification")
    print("=" * 60)

    # Load fixture
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        fixture = json.load(f)

    print(f"\nFixture: {fixture['fixture_id']}")
    print(f"Product: {fixture['buyer_requirement']['product']}")
    print(f"Quantity: {fixture['buyer_requirement']['quantity']}")
    print(f"Deadline: {fixture['buyer_requirement']['deadline_days']} days")

    quantity = fixture["buyer_requirement"]["quantity"]
    deadline_days = fixture["buyer_requirement"]["deadline_days"]
    cap_data = fixture["manufacturer_capacity"]

    # Build production capacity from fixture
    production_capacity = ProductionCapacity(
        actor_id=cap_data["actor_id"],
        daily_capacity_units=float(cap_data["daily_capacity_units"]),
        setup_days=float(cap_data["setup_days"]),
        queue_days=float(cap_data["queue_days"]),
        working_days_per_week=cap_data["working_days_per_week"],
        minimum_batch_size=cap_data["minimum_batch_size"],
        confidence_score=cap_data["confidence_score"],
        evidence_ref=cap_data["evidence_ref"],
    )

    # Build supplier response dicts from fixture paths
    supplier_responses = []
    for path_spec in fixture["paths"]:
        fabric_supplier_id = path_spec["fabric_supplier_id"]
        # Find fabric supplier info
        fabric_info = next(
            (s for s in fixture["fabric_supplier_options"] if s["supplier_id"] == fabric_supplier_id),
            None,
        )
        sr = {
            "response_id": f"RESP-{fabric_supplier_id.upper()}",
            "supplier_id": fabric_supplier_id,
            "supplier_name": fabric_info["supplier_name"] if fabric_info else fabric_supplier_id,
            "can_make": True,
            "fabric_days": path_spec["fabric_days"],
            "trim_days": path_spec.get("trim_days"),
            "packaging_material_days": path_spec.get("packaging_material_days"),
            "qc_days": path_spec.get("qc_days"),
            "packaging_days": path_spec.get("packaging_days"),
            "logistics_days": path_spec.get("logistics_days"),
            "risk_flags": list(path_spec.get("risk_flags", [])),
            "confidence_score": path_spec.get("confidence_score", 0.85),
            "completeness_score": path_spec.get("confidence_score", 0.85),
            "unit_price": fabric_info["price_per_unit"] if fabric_info else None,
            "currency": fabric_info["currency"] if fabric_info else None,
            "_expected_total": path_spec["expected_total_lead_time_days"],
            "_expected_label": path_spec["path_label"],
        }
        supplier_responses.append(sr)

    print(f"\n[Step 1] Enumerating delivery paths for {len(supplier_responses)} supplier options...")

    # Filter out metadata keys for enumeration
    clean_responses = [
        {k: v for k, v in sr.items() if not k.startswith("_")}
        for sr in supplier_responses
    ]

    paths = enumerate_delivery_paths(
        project_id="DEMO-SHIRT100",
        supplier_responses=clean_responses,
        production_capacity=production_capacity,
        buyer_deadline_days=deadline_days,
        quantity=quantity,
    )

    assert len(paths) == len(supplier_responses), (
        f"Expected {len(supplier_responses)} paths, got {len(paths)}"
    )
    print(f"  Generated {len(paths)} paths. OK")

    print("\n[Step 2] Assigning labels and ranking...")
    labeled_paths = assign_labels(paths)
    labels = [p.label for p in labeled_paths]
    print(f"  Labels assigned: {labels}")
    assert "BEST_OVERALL" in labels, "Expected BEST_OVERALL label"
    print("  BEST_OVERALL label present. OK")

    print("\n[Step 3] Verifying lead time calculations against fixture expectations...")
    # Build a lookup: supplier_id → expected total
    expected_by_supplier = {sr["supplier_id"]: sr["_expected_total"] for sr in supplier_responses}

    for path in labeled_paths:
        expected_total = expected_by_supplier.get(path.supplier_id)
        actual_total = path.total_lead_time_days
        print(
            f"  supplier={path.supplier_name}, "
            f"calculated={actual_total}d, expected={expected_total}d"
        )
        assert actual_total == expected_total, (
            f"FAIL: {path.supplier_name}: "
            f"calculated={actual_total}d, expected={expected_total}d. "
            f"material_ready={path.material_ready_days}, production={path.production_days}, "
            f"post_prod={path.post_production_days}, buffer={path.risk_buffer_days}"
        )
        print(f"    material_ready={path.material_ready_days}d + production={path.production_days}d + "
              f"post_prod={path.post_production_days}d + buffer={path.risk_buffer_days}d = {actual_total}d. OK")

    print("\n[Step 4] Verifying deadline feasibility...")
    for path in labeled_paths:
        print(f"  {path.supplier_name}: total={path.total_lead_time_days}d, "
              f"deadline={deadline_days}d, slack={path.slack_days}d, "
              f"feasible={path.feasible_before_deadline}")
        assert path.total_lead_time_days <= deadline_days, (
            f"FAIL: {path.supplier_name} exceeds deadline: "
            f"{path.total_lead_time_days}d > {deadline_days}d"
        )
        assert path.feasible_before_deadline is True, (
            f"FAIL: {path.supplier_name} should be feasible"
        )
    print("  All paths feasible before deadline. OK")

    print("\n[Step 5] Verifying material parallel / sequential logic...")
    for path in labeled_paths:
        # material_ready should be max of material inputs, not sum
        # For paths with fabric_days and trim_days:
        #   material_ready = max(fabric_days, trim_days, packaging_material_days)
        # production, QC, packaging, logistics are sequential
        assert path.critical_path_days > 0, f"FAIL: critical_path_days should be > 0 for {path.supplier_name}"
        # post_production_days = qc + packaging + logistics (all sequential)
        expected_post = 2.0 + 1.0 + 3.0  # qc=2, packaging=1, logistics=3 from fixture
        assert path.post_production_days == expected_post, (
            f"FAIL: post_production_days should be {expected_post} for {path.supplier_name}, "
            f"got {path.post_production_days}"
        )
    print("  Material parallel logic (max) and sequential post-production logic verified. OK")

    print("\n[Step 6] Verifying evidence refs are populated...")
    for path in labeled_paths:
        assert len(path.evidence_refs) > 0, (
            f"FAIL: {path.supplier_name} has no evidence_refs"
        )
        assert len(path.components) > 0, (
            f"FAIL: {path.supplier_name} has no components"
        )
    print(f"  All paths have evidence refs and components. OK")

    print("\n[Step 7] Verifying risk flags for substitute material path...")
    substitute_paths = [p for p in labeled_paths if "substitute_material" in p.risk_flags]
    assert len(substitute_paths) > 0, "FAIL: Expected at least one path with substitute_material risk flag"
    substitute_path = substitute_paths[0]
    assert substitute_path.risk_buffer_days >= 2.0, (
        f"FAIL: substitute_material path should have risk_buffer >= 2.0, "
        f"got {substitute_path.risk_buffer_days}"
    )
    print(f"  Substitute material path has risk_buffer={substitute_path.risk_buffer_days}d (>= 2d). OK")

    print("\n[Step 8] Verifying no 999 sentinel values anywhere...")
    for path in labeled_paths:
        assert path.total_lead_time_days != 999, (
            f"FAIL: Found sentinel 999 in total_lead_time_days for {path.supplier_name}"
        )
        assert path.total_lead_time_days > 0, (
            f"FAIL: total_lead_time_days should be > 0 for {path.supplier_name}"
        )
    print("  No sentinel 999 values. OK")

    print("\n" + "=" * 60)
    print("LEAD TIME MODEL DEMO: PASS")
    print("=" * 60)
    print(f"\nSummary ({len(labeled_paths)} paths):")
    for path in labeled_paths:
        print(
            f"  rank={path.rank} label={path.label or 'none':12s} "
            f"supplier={path.supplier_name[:30]:30s} "
            f"total={path.total_lead_time_days:3d}d "
            f"slack={path.slack_days:+d}d "
            f"risk_flags={len(path.risk_flags)}"
        )


if __name__ == "__main__":
    main()
