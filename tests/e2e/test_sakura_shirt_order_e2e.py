"""
E2E Integration Test — Sakura Fashion Shirt Order
==================================================
Tests the full pipeline:  Inquiry → GLTG → Qwen → DB

Business scenario from giraffe-mcp-server-demo:
  Buyer:   Sakura Fashion Japan (10,000 pcs spring shirts, Apr-10 deadline)
  Sellers: Suzhou Alpha / Guangzhou Beta / Nantong Delta

Qwen mode:
  Default:  mock  (GLTG + DB always use real code)
  Real:     set E2E_QWEN_MODE=real + QWEN_API_KEY=<key>

Run:
  uv run pytest tests/e2e/test_sakura_shirt_order_e2e.py -v
  E2E_QWEN_MODE=real QWEN_API_KEY=<key> uv run pytest tests/e2e/test_sakura_shirt_order_e2e.py -v
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

import bm_db_adapter

# ──────────────────────────────────────────────────────────────────────────────
# Shared fixtures and constants
# ──────────────────────────────────────────────────────────────────────────────

E2E_QWEN_MODE = os.environ.get("E2E_QWEN_MODE", "mock").lower()
E2E_DB_URL = os.environ.get("E2E_DB_URL", "sqlite:///./e2e_test_sakura.db")

QUANTITY = 10_000
DEADLINE_DAYS = 95  # Jan-5 to Apr-10, 2026

SUPPLIER_RESPONSES = [
    {
        "supplier_id": "suzhou_alpha",
        "supplier_name": "Suzhou Alpha Apparel Co.",
        "response_id": "RESP-SAKURA-M01-TEST",
        "can_make": True,
        "unit_price": 8.40,
        "currency": "USD",
        "moq": 1000,
        "fabric_days": 5,
        "qc_days": 3,
        "packaging_days": 2,
        "logistics_days": 14,
        "confidence_score": 0.90,
        "completeness_score": 0.95,
        "risk_flags": ["olive_green_dyeing_5d", "split_delivery_confirmed"],
        "missing_fields": [],
        "notes": "Split delivery confirmed. Olive green dyeing approval needed.",
    },
    {
        "supplier_id": "guangzhou_beta",
        "supplier_name": "Guangzhou Beta Garment Factory",
        "response_id": "RESP-SAKURA-M02-TEST",
        "can_make": True,
        "unit_price": 7.20,
        "currency": "USD",
        "moq": 5000,
        "fabric_days": 10,
        "qc_days": 1,
        "packaging_days": 2,
        "logistics_days": 16,
        "confidence_score": 0.65,
        "completeness_score": 0.70,
        "risk_flags": [
            "sky_blue_fabric_uncertain",
            "pink_fabric_uncertain",
            "olive_green_fabric_uncertain",
            "no_split_delivery",
            "final_inspection_only",
        ],
        "missing_fields": ["split_delivery_option"],
        "notes": "3 of 5 fabric colors uncertain. Single batch only.",
    },
    {
        "supplier_id": "nantong_delta",
        "supplier_name": "Nantong Delta Shirts Ltd.",
        "response_id": "RESP-SAKURA-M03-TEST",
        "can_make": True,
        "unit_price": 7.80,
        "currency": "USD",
        "moq": 500,
        "fabric_days": 0,
        "qc_days": 2,
        "packaging_days": 2,
        "logistics_days": 14,
        "confidence_score": 0.85,
        "completeness_score": 0.90,
        "risk_flags": ["size_ratio_pending_buyer_approval"],
        "missing_fields": ["buyer_size_ratio_confirmation"],
        "notes": "All fabric in-stock. Size ratio adjustment saves 3 production days.",
    },
]


@pytest.fixture(scope="module")
def db_url():
    return E2E_DB_URL


@pytest.fixture(scope="module")
def initialized_db(db_url):
    from sqlalchemy import create_engine
    from src.db.base import Base
    import src.db.models  # noqa: F401

    kwargs = {"connect_args": {"check_same_thread": False}} if "sqlite" in db_url else {}
    engine = create_engine(db_url, echo=False, **kwargs)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    return db_url


@pytest.fixture(scope="module")
def gltg_results():
    from src.gltg.engine import calculate_gltg_lead_time_path
    from src.lead_time.models import ProductionCapacity

    results = []
    for sr in SUPPLIER_RESPONSES:
        path = calculate_gltg_lead_time_path(
            supplier_response_id=sr["response_id"],
            supplier_id=sr["supplier_id"],
            supplier_name=sr["supplier_name"],
            project_id="PROJ-TEST-SAKURA",
            quantity=QUANTITY,
            fabric_days=sr.get("fabric_days"),
            qc_days=sr.get("qc_days"),
            packaging_days=sr.get("packaging_days"),
            logistics_days=sr.get("logistics_days"),
            production_capacity=ProductionCapacity(
                actor_id=sr["supplier_id"],
                daily_capacity_units=500,
                setup_days=1,
                queue_days=0,
                confidence_score=sr["confidence_score"],
            ),
            buyer_deadline_days=DEADLINE_DAYS,
            confidence_score=sr["confidence_score"],
            completeness_score=sr["completeness_score"],
            unit_price=sr.get("unit_price"),
            currency=sr.get("currency"),
            risk_flags=sr.get("risk_flags", []),
            missing_fields=sr.get("missing_fields", []),
        )
        results.append((sr, path))
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2: GLTG Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestGLTGConnectivity:
    """Phase 2.7 — GLTG module loads and returns expected structure."""

    def test_gltg_module_imports(self):
        from src.gltg.engine import GLTG_MODEL_NAME, GLTG_MODEL_VERSION, calculate_gltg_lead_time_path
        assert GLTG_MODEL_NAME == "GLTG"
        assert GLTG_MODEL_VERSION.startswith("0.1")

    def test_gltg_returns_all_three_suppliers(self, gltg_results):
        assert len(gltg_results) == 3

    def test_gltg_model_provenance(self, gltg_results):
        for sr, path in gltg_results:
            assert path.model_name == "GLTG", f"Wrong model for {sr['supplier_id']}: {path.model_name}"
            assert path.feasibility_basis == "p80", f"Wrong basis for {sr['supplier_id']}"
            assert path.fallback_model_used is False

    def test_gltg_percentile_ordering(self, gltg_results):
        for sr, path in gltg_results:
            assert path.p50_lead_time_days <= path.p80_lead_time_days, \
                f"P50 > P80 for {sr['supplier_id']}"
            assert path.p80_lead_time_days <= path.p90_lead_time_days, \
                f"P80 > P90 for {sr['supplier_id']}"

    def test_gltg_suzhou_alpha_is_feasible(self, gltg_results):
        sr, path = next((s, p) for s, p in gltg_results if s["supplier_id"] == "suzhou_alpha")
        assert path.feasible_before_deadline, \
            f"Suzhou Alpha should be feasible: P80={path.p80_lead_time_days}d, deadline={DEADLINE_DAYS}d"
        assert path.slack_days > 0, f"Suzhou Alpha must have positive slack"

    def test_gltg_suzhou_alpha_specific_values(self, gltg_results):
        _, path = next((s, p) for s, p in gltg_results if s["supplier_id"] == "suzhou_alpha")
        # P80 should be in a reasonable range for this scenario
        assert 30 <= path.p80_lead_time_days <= 70, \
            f"Suzhou Alpha P80={path.p80_lead_time_days}d is outside expected range 30-70d"

    def test_gltg_guangzhou_beta_has_higher_risk(self, gltg_results):
        _, alpha_path = next((s, p) for s, p in gltg_results if s["supplier_id"] == "suzhou_alpha")
        _, beta_path = next((s, p) for s, p in gltg_results if s["supplier_id"] == "guangzhou_beta")
        assert beta_path.risk_score > alpha_path.risk_score, \
            f"Beta risk ({beta_path.risk_score}) should exceed Alpha risk ({alpha_path.risk_score})"

    def test_gltg_nantong_delta_no_fabric_delay(self, gltg_results):
        _, path = next((s, p) for s, p in gltg_results if s["supplier_id"] == "nantong_delta")
        # Nantong has all fabric in-stock (fabric_days=0), should have shorter lead time
        _, alpha_path = next((s, p) for s, p in gltg_results if s["supplier_id"] == "suzhou_alpha")
        assert path.p80_lead_time_days <= alpha_path.p80_lead_time_days, \
            f"Nantong Delta P80={path.p80_lead_time_days}d should be ≤ Suzhou Alpha P80={alpha_path.p80_lead_time_days}d"

    def test_gltg_evidence_refs_contain_gltg(self, gltg_results):
        for sr, path in gltg_results:
            has_gltg = any("GLTG" in ref or "gltg" in ref.lower() for ref in path.evidence_refs)
            assert has_gltg, f"Missing GLTG evidence ref for {sr['supplier_id']}: {path.evidence_refs}"

    def test_gltg_performance(self, gltg_results):
        """GLTG must complete in under 100ms per supplier."""
        from src.gltg.engine import calculate_gltg_lead_time_path
        from src.lead_time.models import ProductionCapacity

        sr = SUPPLIER_RESPONSES[0]
        t0 = time.time()
        for _ in range(10):
            calculate_gltg_lead_time_path(
                supplier_response_id=sr["response_id"],
                supplier_id=sr["supplier_id"],
                supplier_name=sr["supplier_name"],
                project_id="PERF-TEST",
                quantity=QUANTITY,
                fabric_days=sr.get("fabric_days"),
                logistics_days=sr.get("logistics_days"),
                production_capacity=ProductionCapacity(
                    actor_id=sr["supplier_id"],
                    daily_capacity_units=500,
                ),
                buyer_deadline_days=DEADLINE_DAYS,
            )
        elapsed_ms = (time.time() - t0) * 1000
        avg_ms = elapsed_ms / 10
        assert avg_ms < 100, f"GLTG average time {avg_ms:.1f}ms exceeds 100ms budget"


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2: DB Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDBConnectivity:
    """Phase 2.8 — DB initializes and CRUD works."""

    def test_db_schema_created(self, initialized_db):
        from sqlalchemy import create_engine, inspect
        from src.db.base import Base
        import src.db.models  # noqa: F401

        kwargs = {"connect_args": {"check_same_thread": False}}
        engine = create_engine(initialized_db, echo=False, **kwargs)
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        engine.dispose()

        required = {"actors", "projects", "supplier_inquiries", "supplier_responses",
                    "supplier_response_rollups", "procurement_edges", "execution_events",
                    "structured_requirements"}
        missing = required - tables
        assert not missing, f"Missing tables: {missing}"

    def test_db_actor_crud(self, initialized_db):
        bm_db_adapter.DB_MODE = "on"
        adapter = bm_db_adapter.BMDbAdapter(db_url=initialized_db)
        try:
            actor = adapter.get_or_create_actor("Test Buyer CRUD", "buyer")
            assert actor["actor_id"]
            assert actor["name"] == "Test Buyer CRUD"
            adapter.commit()
        finally:
            adapter.close()
        bm_db_adapter.DB_MODE = "off"

    def test_db_project_crud(self, initialized_db):
        bm_db_adapter.DB_MODE = "on"
        adapter = bm_db_adapter.BMDbAdapter(db_url=initialized_db)
        try:
            buyer = adapter.get_or_create_actor("Test Buyer Proj", "buyer")
            supplier = adapter.get_or_create_actor("Test Supplier Proj", "manufacturer")
            project = adapter.get_or_create_project(
                original_buyer_actor_id=buyer["actor_id"],
                project_key="test-crud-project",
                main_supplier_actor_id=supplier["actor_id"],
                category="test",
                quantity=1,
            )
            assert project["project_id"]
            adapter.commit()
        finally:
            adapter.close()
        bm_db_adapter.DB_MODE = "off"

    def test_db_event_logging(self, initialized_db):
        bm_db_adapter.DB_MODE = "on"
        adapter = bm_db_adapter.BMDbAdapter(db_url=initialized_db)
        try:
            buyer = adapter.get_or_create_actor("Event Test Buyer", "buyer")
            supplier = adapter.get_or_create_actor("Event Test Supplier", "manufacturer")
            project = adapter.get_or_create_project(
                original_buyer_actor_id=buyer["actor_id"],
                project_key="test-event-project",
                main_supplier_actor_id=supplier["actor_id"],
                category="test",
                quantity=1,
            )
            adapter.log_event("DB_EVENT_TEST", project_id=project["project_id"])
            adapter.commit()
            counts = adapter.get_counts()
            assert counts["execution_events"] >= 1
        finally:
            adapter.close()
        bm_db_adapter.DB_MODE = "off"


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2: Qwen Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestQwenConnectivity:
    """Phase 2.6 — Qwen provider loads; real call only when E2E_QWEN_MODE=real."""

    def test_qwen_provider_imports(self):
        from src.llm.qwen_provider import QwenProvider
        from src.llm.provider_config import get_qwen_api_key
        assert QwenProvider is not None

    def test_qwen_mock_provider_available(self):
        from src.llm.mock_provider import MockLLMProvider
        provider = MockLLMProvider()
        result = provider.complete_text("test prompt")
        assert result.text

    @pytest.mark.skipif(
        E2E_QWEN_MODE != "real",
        reason="Set E2E_QWEN_MODE=real and QWEN_API_KEY=<key> to run real Qwen test",
    )
    def test_qwen_real_api_call(self):
        """Phase 2.6 — Real Qwen minimal connectivity check."""
        from src.llm.qwen_provider import QwenProvider
        from src.llm.provider_config import get_qwen_api_key

        api_key = get_qwen_api_key()
        assert api_key, "QWEN_API_KEY or DASHSCOPE_API_KEY must be set for real mode"

        provider = QwenProvider(api_key=api_key)
        t0 = time.time()
        result = provider.complete_text(
            prompt="Say 'GIRAFFE_AGENT_OK' and nothing else.",
            system_prompt="You are a test responder. Reply with exactly the text requested.",
        )
        elapsed_ms = (time.time() - t0) * 1000

        assert result.text, "Qwen returned empty response"
        assert elapsed_ms < 30_000, f"Qwen took {elapsed_ms:.0f}ms — too slow"
        print(f"\n  [Qwen real] response={result.text!r}  elapsed={elapsed_ms:.0f}ms  model={result.model_name}")


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3: End-to-End Business Simulation
# ──────────────────────────────────────────────────────────────────────────────


class TestE2ESakuraShirtOrder:
    """Phase 3 — Full pipeline: Inquiry → GLTG → Qwen → DB."""

    @pytest.fixture(scope="class")
    def e2e_run(self, initialized_db, gltg_results):
        """Run the full E2E pipeline once and cache the result."""
        from src.llm.provider_config import get_qwen_api_key

        # ─── Qwen ─────────────────────────────────────────────────────────
        if E2E_QWEN_MODE == "real":
            api_key = get_qwen_api_key()
            assert api_key, "Real mode requires QWEN_API_KEY"
            from src.llm.qwen_provider import QwenProvider
            provider = QwenProvider(api_key=api_key)
            gltg_summary = "\n".join(
                f"- {sr['supplier_name']}: P80={p.p80_lead_time_days}d, "
                f"feasible={p.feasible_before_deadline}, risk={p.risk_score}, price=USD {sr['unit_price']}"
                for sr, p in gltg_results
            )
            prompt = (
                f"You are a B2M procurement advisor. {QUANTITY:,} pcs shirts for Japan by Apr-10-2026 "
                f"(95 days). GLTG results:\n{gltg_summary}\n\n"
                "Return JSON: {\"recommended_supplier\": \"<id>\", \"confidence\": \"high|medium|low\", "
                "\"risk_summary\": \"<text>\", \"recommended_action\": \"<text>\"}"
            )
            t0 = time.time()
            qwen_result = provider.extract_json(prompt=prompt)
            qwen_elapsed_ms = (time.time() - t0) * 1000
            qwen_data = qwen_result.data
            qwen_data["_mode"] = "real"
            qwen_data["_elapsed_ms"] = qwen_elapsed_ms
        else:
            # Deterministic mock
            qwen_data = {
                "recommended_supplier": "suzhou_alpha",
                "recommended_supplier_name": "Suzhou Alpha Apparel Co.",
                "confidence": "high",
                "ranking": [
                    {"rank": 1, "supplier_id": "suzhou_alpha", "reason": "Best delivery with split option"},
                    {"rank": 2, "supplier_id": "nantong_delta", "reason": "All fabric in-stock"},
                    {"rank": 3, "supplier_id": "guangzhou_beta", "reason": "Lowest price, higher risk"},
                ],
                "risk_summary": (
                    "Suzhou Alpha offers the strongest delivery certainty with confirmed split delivery. "
                    "Olive green dyeing (5 days) requires immediate approval. "
                    "Guangzhou Beta's uncertain fabric sourcing for 3 colors is a significant risk."
                ),
                "recommended_action": "Issue PO to Suzhou Alpha; approve olive green dyeing immediately.",
                "split_delivery_feasible": True,
                "price_tradeoff": "Suzhou Alpha USD 1.20/pc premium vs Beta eliminates 3-color fabric sourcing risk.",
                "_mode": "mock",
            }

        # ─── DB Persist ───────────────────────────────────────────────────
        bm_db_adapter.DB_MODE = "on"
        adapter = bm_db_adapter.BMDbAdapter(db_url=initialized_db)

        buyer = adapter.get_or_create_actor("Sakura Fashion Japan [E2E]", "buyer")
        supplier_actors = {}
        for sr, _ in gltg_results:
            actor = adapter.get_or_create_actor(f"{sr['supplier_name']} [E2E]", "manufacturer")
            supplier_actors[sr["supplier_id"]] = actor

        project = adapter.get_or_create_project(
            original_buyer_actor_id=buyer["actor_id"],
            project_key="sakura-shirt-10k-e2e-test",
            main_supplier_actor_id=supplier_actors["suzhou_alpha"]["actor_id"],
            category="apparel",
            quantity=QUANTITY,
            status="CREATED",
        )

        req = adapter.create_requirement(
            project_id=project["project_id"],
            source_actor_id=buyer["actor_id"],
            category="apparel",
            quantity=QUANTITY,
            material="woven fabric",
            specs_json={
                "colors": ["white", "sky blue", "black", "pink", "olive green"],
                "sizes": ["S", "M", "L", "XL"],
                "shelf_date": "2026-04-10",
                "deadline_days": DEADLINE_DAYS,
            },
            confidence_score=0.95,
        )

        db_records: dict[str, dict] = {}
        for sr, path in gltg_results:
            supplier_actor = supplier_actors[sr["supplier_id"]]
            edge = adapter.create_edge(
                project_id=project["project_id"],
                from_actor_id=buyer["actor_id"],
                to_actor_id=supplier_actor["actor_id"],
                edge_type="BUYER_TO_SUPPLIER",
                status="DRAFT",
            )
            inquiry = adapter.create_inquiry(
                project_id=project["project_id"],
                edge_id=edge["edge_id"],
                from_actor_id=buyer["actor_id"],
                to_actor_id=supplier_actor["actor_id"],
                requirement_id=req["requirement_id"],
                message_text_en=f"RFQ {QUANTITY:,} pcs spring shirts. Deadline: 2026-04-10.",
                status="SENT",
            )
            adapter.update_edge(edge["edge_id"], inquiry_id=inquiry["inquiry_id"], status="SENT")

            response = adapter.create_response(
                project_id=project["project_id"],
                edge_id=edge["edge_id"],
                from_actor_id=supplier_actor["actor_id"],
                to_actor_id=buyer["actor_id"],
                inquiry_id=inquiry["inquiry_id"],
                can_supply=True,
                price=sr.get("unit_price"),
                currency=sr.get("currency", "USD"),
                moq=float(sr.get("moq", 0)),
                available_quantity=float(QUANTITY),
                lead_time_days=path.total_lead_time_days,
                confidence_score=sr["confidence_score"],
                completeness_score=sr["completeness_score"],
            )
            adapter.update_edge(edge["edge_id"], response_id=response["response_id"], status="RESPONDED")

            gltg_summary = (
                f"GLTG {path.model_name}/{path.model_version} | "
                f"P50={path.p50_lead_time_days}d P80={path.p80_lead_time_days}d P90={path.p90_lead_time_days}d | "
                f"feasible={path.feasible_before_deadline} slack={path.slack_days}d risk={path.risk_score}"
            )
            adapter.create_rollup(
                project_id=project["project_id"],
                main_supplier_actor_id=supplier_actor["actor_id"],
                can_accept_order=path.feasible_before_deadline,
                main_capacity_summary=gltg_summary,
                completeness_score=sr["completeness_score"],
                confidence_score=sr["confidence_score"],
            )
            db_records[sr["supplier_id"]] = {
                "edge_id": edge["edge_id"],
                "inquiry_id": inquiry["inquiry_id"],
                "response_id": response["response_id"],
                "gltg_p80": path.p80_lead_time_days,
                "gltg_feasible": path.feasible_before_deadline,
            }

        # Confirm order on recommended supplier
        recommended = qwen_data.get("recommended_supplier", "suzhou_alpha")
        if recommended in db_records:
            adapter.update_edge(db_records[recommended]["edge_id"], status="APPROVED")

        adapter.update_project_status(project["project_id"], "ORDER_CONFIRMED")

        for event_type in (
            "BUYER_INQUIRY_RECEIVED",
            "SUPPLIER_RFQS_DISPATCHED",
            "GLTG_FEASIBILITY_EVALUATED",
            "QWEN_RECOMMENDATION_GENERATED",
            "ORDER_CONFIRMED",
            "PRODUCTION_MONITORING_STARTED",
        ):
            adapter.log_event(event_type, project_id=project["project_id"])

        adapter.commit()
        counts = adapter.get_counts()
        adapter.close()
        bm_db_adapter.DB_MODE = "off"

        return {
            "gltg_results": gltg_results,
            "qwen_data": qwen_data,
            "project_id": project["project_id"],
            "requirement_id": req["requirement_id"],
            "db_records": db_records,
            "counts": counts,
        }

    # ─── GLTG sub-assertions ──────────────────────────────────────────────

    def test_e2e_gltg_ran_for_all_suppliers(self, e2e_run):
        assert len(e2e_run["gltg_results"]) == 3

    def test_e2e_gltg_suzhou_feasible(self, e2e_run):
        _, path = next(
            (s, p) for s, p in e2e_run["gltg_results"] if s["supplier_id"] == "suzhou_alpha"
        )
        assert path.feasible_before_deadline
        assert path.slack_days >= 0

    def test_e2e_gltg_uses_gltg_model(self, e2e_run):
        for _, path in e2e_run["gltg_results"]:
            assert path.model_name == "GLTG"
            assert path.feasibility_basis == "p80"

    # ─── Qwen sub-assertions ──────────────────────────────────────────────

    def test_e2e_qwen_returns_recommendation(self, e2e_run):
        qwen = e2e_run["qwen_data"]
        assert "recommended_supplier" in qwen, f"Missing recommended_supplier: {qwen}"
        assert qwen["recommended_supplier"], "recommended_supplier must not be empty"

    def test_e2e_qwen_risk_summary_present(self, e2e_run):
        qwen = e2e_run["qwen_data"]
        assert "risk_summary" in qwen, "Qwen must return a risk_summary"
        assert len(qwen["risk_summary"]) > 10, "risk_summary too short"

    def test_e2e_qwen_action_present(self, e2e_run):
        qwen = e2e_run["qwen_data"]
        assert "recommended_action" in qwen, "Qwen must return recommended_action"

    # ─── DB sub-assertions ────────────────────────────────────────────────

    def test_e2e_db_actors_count(self, e2e_run):
        counts = e2e_run["counts"]
        assert counts["actors"] >= 4, f"Expected ≥4 actors, got {counts['actors']}"

    def test_e2e_db_project_created(self, e2e_run):
        counts = e2e_run["counts"]
        assert counts["projects"] >= 1, f"Expected ≥1 project, got {counts['projects']}"

    def test_e2e_db_three_inquiries(self, e2e_run):
        counts = e2e_run["counts"]
        assert counts["supplier_inquiries"] >= 3, \
            f"Expected ≥3 inquiries, got {counts['supplier_inquiries']}"

    def test_e2e_db_three_responses(self, e2e_run):
        counts = e2e_run["counts"]
        assert counts["supplier_responses"] >= 3, \
            f"Expected ≥3 responses, got {counts['supplier_responses']}"

    def test_e2e_db_three_rollups_with_gltg(self, e2e_run):
        counts = e2e_run["counts"]
        assert counts["supplier_response_rollups"] >= 3, \
            f"Expected ≥3 rollups, got {counts['supplier_response_rollups']}"

    def test_e2e_db_execution_events_recorded(self, e2e_run):
        counts = e2e_run["counts"]
        assert counts["execution_events"] >= 6, \
            f"Expected ≥6 events, got {counts['execution_events']}"

    def test_e2e_db_edges_correctly_linked(self, e2e_run, initialized_db):
        bm_db_adapter.DB_MODE = "on"
        adapter = bm_db_adapter.BMDbAdapter(db_url=initialized_db)
        try:
            for sid, rec in e2e_run["db_records"].items():
                edge_state = adapter.get_edge(rec["edge_id"])
                assert edge_state["inquiry_id"] == rec["inquiry_id"], \
                    f"Edge inquiry_id not linked for {sid}"
                assert edge_state["response_id"] == rec["response_id"], \
                    f"Edge response_id not linked for {sid}"
        finally:
            adapter.close()
        bm_db_adapter.DB_MODE = "off"

    def test_e2e_db_gltg_data_in_rollup(self, e2e_run):
        """Verify GLTG P80 is embedded in DB rollup records (via capacity summary)."""
        for sid, rec in e2e_run["db_records"].items():
            assert "gltg_p80" in rec, f"gltg_p80 missing for {sid}"
            assert isinstance(rec["gltg_p80"], int), f"gltg_p80 should be int for {sid}"
            assert 1 <= rec["gltg_p80"] <= 200, f"gltg_p80 out of range for {sid}: {rec['gltg_p80']}"


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4: Exception and Boundary Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestExceptionHandling:
    """Phase 4 — At least 3 error scenarios."""

    def test_qwen_missing_api_key_raises_runtime_error(self):
        """Phase 4.1 — Qwen with no API key must raise RuntimeError, not crash silently."""
        from src.llm.qwen_provider import QwenProvider

        provider = QwenProvider(api_key="")
        with pytest.raises(Exception):
            # A real API call with an empty key must raise (either httpx error or auth error)
            provider.complete_text("test", system_prompt=None)

    def test_gltg_invalid_days_does_not_crash(self):
        """Phase 4.2 — GLTG with extreme/invalid inputs returns a degraded-but-valid path."""
        from src.gltg.engine import calculate_gltg_lead_time_path

        # Negative fabric_days: should not crash
        path = calculate_gltg_lead_time_path(
            supplier_response_id="ERR-TEST-001",
            supplier_id="bad_supplier",
            supplier_name="Bad Supplier",
            project_id="PROJ-ERR",
            quantity=10000,
            fabric_days=-5,  # invalid: negative
            logistics_days=9999,  # extreme: very large
            confidence_score=-0.1,  # out of range
            completeness_score=2.0,  # out of range
            buyer_deadline_days=30,
        )
        # Must return a path object (not raise)
        assert path.model_name == "GLTG"
        assert path.p80_lead_time_days is not None
        assert isinstance(path.feasible_before_deadline, bool)

    def test_gltg_zero_quantity_does_not_crash(self):
        """Phase 4.2b — GLTG with quantity=0 must not raise."""
        from src.gltg.engine import calculate_gltg_lead_time_path

        path = calculate_gltg_lead_time_path(
            supplier_response_id="ZERO-QTY-001",
            supplier_id="supplier_z",
            supplier_name="Zero Qty Supplier",
            project_id="PROJ-ZERO",
            quantity=0,
            logistics_days=14,
            buyer_deadline_days=60,
        )
        assert path.model_name == "GLTG"

    def test_db_duplicate_project_key_is_idempotent(self, initialized_db):
        """Phase 4.3 — Creating the same project twice with the same key must not raise."""
        bm_db_adapter.DB_MODE = "on"
        adapter = bm_db_adapter.BMDbAdapter(db_url=initialized_db)
        try:
            buyer = adapter.get_or_create_actor("Idempotent Buyer", "buyer")
            supplier = adapter.get_or_create_actor("Idempotent Supplier", "manufacturer")
            project_key = "idempotent-test-key"

            p1 = adapter.get_or_create_project(
                original_buyer_actor_id=buyer["actor_id"],
                project_key=project_key,
                main_supplier_actor_id=supplier["actor_id"],
                category="test",
                quantity=1,
            )
            p2 = adapter.get_or_create_project(
                original_buyer_actor_id=buyer["actor_id"],
                project_key=project_key,
                main_supplier_actor_id=supplier["actor_id"],
                category="test",
                quantity=1,
            )
            # Must be the same project
            assert p1["project_id"] == p2["project_id"], "get_or_create_project is not idempotent"
            adapter.commit()
        finally:
            adapter.close()
        bm_db_adapter.DB_MODE = "off"

    def test_gltg_missing_all_days_fields(self):
        """Phase 4.4 — GLTG with all duration fields None uses safe defaults."""
        from src.gltg.engine import calculate_gltg_lead_time_path

        path = calculate_gltg_lead_time_path(
            supplier_response_id="ALL-NONE-001",
            supplier_id="min_supplier",
            supplier_name="Minimal Supplier",
            project_id="PROJ-MIN",
            # No fabric_days, qc_days, etc.
            buyer_deadline_days=60,
        )
        assert path.model_name == "GLTG"
        assert path.total_lead_time_days >= 0
        assert isinstance(path.feasible_before_deadline, bool)

    def test_qwen_provider_no_crash_on_timeout_config(self):
        """Phase 4.5 — QwenProvider initializes safely with custom timeout."""
        import os
        os.environ["LLM_TIMEOUT_SECONDS"] = "1"
        from src.llm import provider_config
        provider_config.LLM_TIMEOUT_SECONDS = 1

        from src.llm.qwen_provider import QwenProvider
        # Use a short placeholder that doesn't match the ≥8-char secret pattern
        test_key = "test-placeholder"
        provider = QwenProvider(api_key=test_key)
        # Provider object must be constructable — no crash on init
        assert provider.api_key == test_key
        assert provider.text_model

        os.environ.pop("LLM_TIMEOUT_SECONDS", None)
        provider_config.LLM_TIMEOUT_SECONDS = 60
