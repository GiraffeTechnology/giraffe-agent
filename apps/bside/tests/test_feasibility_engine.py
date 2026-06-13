"""
Tests for B-side feasibility simulation engine.
"""
import uuid
import pytest
from src.b_side.feasibility_engine import _score_response, _build_path, run_feasibility_simulation
from src.core_schema.b_side_types import (
    BWWorkspace, BuyerRequirement, SupplierResponseRecord, DeliveryPath
)


# ─── _score_response ─────────────────────────────────────────────────────────

class TestScoreResponse:
    def _make_response(self, lead_time=30, confidence=0.9, red_flags=None):
        return SupplierResponseRecord(
            response_id="RSP-001",
            rfq_id="RFQ-001",
            b_workspace_id="bw_001",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
            estimated_lead_time_days=lead_time,
            confidence_score=confidence,
            red_flags=red_flags or [],
        )

    def test_score_is_float(self):
        r = self._make_response()
        score = _score_response(r)
        assert isinstance(score, float)

    def test_higher_confidence_higher_score(self):
        r_high = self._make_response(confidence=0.9)
        r_low = self._make_response(confidence=0.3)
        assert _score_response(r_high) > _score_response(r_low)

    def test_shorter_lead_time_higher_score(self):
        r_fast = self._make_response(lead_time=10, confidence=0.9)
        r_slow = self._make_response(lead_time=60, confidence=0.9)
        assert _score_response(r_fast) > _score_response(r_slow)

    def test_red_flags_lower_score(self):
        r_clean = self._make_response(red_flags=[])
        r_flagged = self._make_response(red_flags=["capacity uncertain", "price invalid"])
        assert _score_response(r_clean) > _score_response(r_flagged)

    def test_no_lead_time_penalized(self):
        r_no_lead = self._make_response(lead_time=None)
        r_with_lead = self._make_response(lead_time=30)
        assert _score_response(r_with_lead) > _score_response(r_no_lead)

    def test_score_is_positive(self):
        r = self._make_response()
        assert _score_response(r) > 0

    def test_score_capped_by_confidence(self):
        r = self._make_response(lead_time=1, confidence=0.5)
        assert _score_response(r) <= 1.0

    def test_multiple_red_flags_compound_penalty(self):
        r_one_flag = self._make_response(red_flags=["issue1"])
        r_many_flags = self._make_response(red_flags=["i1", "i2", "i3", "i4"])
        assert _score_response(r_one_flag) > _score_response(r_many_flags)


# ─── _build_path ─────────────────────────────────────────────────────────────

class TestBuildPath:
    def _make_response(self, **kwargs):
        defaults = dict(
            response_id="RSP-001",
            rfq_id="RFQ-001",
            b_workspace_id="bw_001",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
            estimated_lead_time_days=20,
            unit_price=10.0,
            total_price=1000.0,
            currency="USD",
            confidence_score=0.9,
        )
        defaults.update(kwargs)
        return SupplierResponseRecord(**defaults)

    def test_path_id_starts_with_path(self):
        r = self._make_response()
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.path_id.startswith("PATH-")

    def test_rank_assigned(self):
        r = self._make_response()
        path = _build_path(r, "RFQ-001", rank=2)
        assert path.rank == 2

    def test_supplier_id_preserved(self):
        r = self._make_response(supplier_id="sup_specific")
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.supplier_id == "sup_specific"

    def test_lead_time_preserved(self):
        r = self._make_response(estimated_lead_time_days=25)
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.lead_time_days == 25

    def test_price_preserved(self):
        r = self._make_response(unit_price=15.50, currency="USD")
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.unit_price == 15.50

    def test_red_flags_become_notes(self):
        r = self._make_response(red_flags=["capacity risk", "price pending"])
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.notes is not None
        assert "capacity risk" in path.notes

    def test_no_red_flags_notes_none(self):
        r = self._make_response(red_flags=[])
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.notes is None

    def test_risk_score_with_flags(self):
        r = self._make_response(red_flags=["flag1", "flag2"])
        path = _build_path(r, "RFQ-001", rank=1)
        assert path.risk_score > 0


# ─── run_feasibility_simulation ──────────────────────────────────────────────

class TestRunFeasibilitySimulation:
    def _setup_workspace(self, bw_id, tmp_path, monkeypatch, responses):
        import src.b_side.workspace as ws_mod
        monkeypatch.setattr(ws_mod, "_DATA_DIR", tmp_path / "bw_feasibility")
        req = BuyerRequirement(
            rfq_id="RFQ-FEA001",
            b_workspace_id=bw_id,
            raw_text="100 pcs cnc bracket",
        )
        ws = BWWorkspace(
            b_workspace_id=bw_id,
            rfq_id="RFQ-FEA001",
            raw_requirement="100 pcs cnc bracket",
            buyer_requirement=req,
            supplier_responses=responses,
        )
        ws_mod._ensure_dir()
        ws_mod.save_b_workspace(ws)

    def _make_response(self, supplier_id, can_make, lead_time=30, confidence=0.8, bw_id="bw_fea"):
        return SupplierResponseRecord(
            response_id=f"RSP-{uuid.uuid4().hex[:6]}",
            rfq_id="RFQ-FEA001",
            b_workspace_id=bw_id,
            supplier_id=supplier_id,
            supplier_name=f"Supplier {supplier_id}",
            can_make=can_make,
            estimated_lead_time_days=lead_time,
            confidence_score=confidence,
        )

    def test_returns_feasibility_report(self, tmp_path, monkeypatch):
        bw_id = "bw_fea001"
        r1 = self._make_response("s1", True, bw_id=bw_id)
        self._setup_workspace(bw_id, tmp_path, monkeypatch, [r1])
        report = run_feasibility_simulation(bw_id)
        assert report.rfq_id == "RFQ-FEA001"

    def test_only_can_make_included(self, tmp_path, monkeypatch):
        bw_id = "bw_fea002"
        r1 = self._make_response("s1", True, bw_id=bw_id)
        r2 = self._make_response("s2", False, bw_id=bw_id)
        r3 = self._make_response("s3", None, bw_id=bw_id)
        self._setup_workspace(bw_id, tmp_path, monkeypatch, [r1, r2, r3])
        report = run_feasibility_simulation(bw_id)
        assert len(report.paths) == 1
        assert report.paths[0].supplier_id == "s1"

    def test_paths_sorted_by_score(self, tmp_path, monkeypatch):
        bw_id = "bw_fea003"
        r_best = self._make_response("best", True, lead_time=10, confidence=0.95, bw_id=bw_id)
        r_worst = self._make_response("worst", True, lead_time=60, confidence=0.5, bw_id=bw_id)
        self._setup_workspace(bw_id, tmp_path, monkeypatch, [r_worst, r_best])
        report = run_feasibility_simulation(bw_id)
        assert len(report.paths) == 2
        assert report.paths[0].supplier_id == "best"
        assert report.paths[0].rank == 1

    def test_empty_responses_returns_empty_paths(self, tmp_path, monkeypatch):
        bw_id = "bw_fea004"
        self._setup_workspace(bw_id, tmp_path, monkeypatch, [])
        report = run_feasibility_simulation(bw_id)
        assert len(report.paths) == 0

    def test_workspace_status_updated(self, tmp_path, monkeypatch):
        import src.b_side.workspace as ws_mod
        bw_id = "bw_fea005"
        r1 = self._make_response("s1", True, bw_id=bw_id)
        self._setup_workspace(bw_id, tmp_path, monkeypatch, [r1])
        run_feasibility_simulation(bw_id)
        ws = ws_mod.get_b_workspace(bw_id)
        assert ws.status == "feasibility_complete"

    def test_paths_have_sequential_ranks(self, tmp_path, monkeypatch):
        bw_id = "bw_fea006"
        responses = [
            self._make_response(f"s{i}", True, lead_time=30-i*5, bw_id=bw_id)
            for i in range(3)
        ]
        self._setup_workspace(bw_id, tmp_path, monkeypatch, responses)
        report = run_feasibility_simulation(bw_id)
        ranks = [p.rank for p in report.paths]
        assert sorted(ranks) == list(range(1, len(ranks) + 1))

    def test_report_persisted_to_workspace(self, tmp_path, monkeypatch):
        import src.b_side.workspace as ws_mod
        bw_id = "bw_fea007"
        r1 = self._make_response("s1", True, bw_id=bw_id)
        self._setup_workspace(bw_id, tmp_path, monkeypatch, [r1])
        run_feasibility_simulation(bw_id)
        ws = ws_mod.get_b_workspace(bw_id)
        assert ws.feasibility_report is not None
