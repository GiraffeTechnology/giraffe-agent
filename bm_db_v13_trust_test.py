"""BM DB Integration v1.3 — Trust Boundary & Rule Integrity test suite.

Covers all v1.0–v1.3 layers:
  Baseline (v1.0)  — verify_integration.py --runs 5 (regression guard)
  Hardening (v1.1) — bm_db_hardening.py (8 suites)
  Replay/DP (v1.2) — execution_graph_replay + decision_packet_generator
  Trust (v1.3)     — rule_packet_registry, evidence_guard, human_confirmation

Usage::

    python bm_db_v13_trust_test.py --db sqlite:///./v13_test.db
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class SuiteResult:
    name: str
    passed: bool
    details: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _banner(text: str) -> None:
    print(f"\n--- {text} ---")


def _pass(suite: SuiteResult, detail: str) -> None:
    suite.details.append(detail)
    print(f"    {detail}")


def _fail(suite: SuiteResult, msg: str) -> AssertionError:
    suite.errors.append(msg)
    suite.passed = False
    print(f"    FAIL: {msg}")
    return AssertionError(msg)


@contextmanager
def _adapter(db_url: str) -> Generator[Any, None, None]:
    """Context manager: commits on clean exit, always closes the session."""
    import bm_db_adapter as bma
    bma.DB_MODE = "on"
    adp = bma.BMDbAdapter(db_url=db_url)
    try:
        yield adp
        adp.commit()
    finally:
        try:
            adp.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Shared lifecycle builder (same pattern as v1.1/v1.2 tests)
# ---------------------------------------------------------------------------

def _build_lifecycle(adapter: Any, run_label: str) -> dict:
    buyer = adapter.get_or_create_actor(
        f"TrustBuyer-{run_label}", "BUYER", default_language="en", is_active=True,
    )
    supplier = adapter.get_or_create_actor(
        f"TrustSupplier-{run_label}", "SUPPLIER", default_language="zh", is_active=True,
    )
    project = adapter.get_or_create_project(
        original_buyer_actor_id=buyer["actor_id"],
        project_key=f"trust-shirts-{run_label}",
        main_supplier_actor_id=supplier["actor_id"],
    )
    req = adapter.create_requirement(
        project_id=project["project_id"],
        source_actor_id=buyer["actor_id"],
        category="Apparel", quantity=200,
        material="Polyester", deadline="2026-10-31", destination="London",
        confidence_score=0.85,
    )
    edge = adapter.create_edge(
        project_id=project["project_id"],
        from_actor_id=buyer["actor_id"],
        to_actor_id=supplier["actor_id"],
        edge_type="MAIN_B_TO_M", status="PENDING",
    )
    inq = adapter.create_inquiry(
        project_id=project["project_id"],
        edge_id=edge["edge_id"],
        from_actor_id=buyer["actor_id"],
        to_actor_id=supplier["actor_id"],
        requirement_id=req["requirement_id"],
        status="SENT",
    )
    adapter.update_edge(edge["edge_id"], inquiry_id=inq["inquiry_id"])
    resp = adapter.create_response(
        project_id=project["project_id"],
        edge_id=edge["edge_id"],
        inquiry_id=inq["inquiry_id"],
        from_actor_id=supplier["actor_id"],
        to_actor_id=buyer["actor_id"],
        can_supply=True,
        price=7.20,
        currency="USD",
        moq=50,
        lead_time_days=25,
        available_quantity=800,
        confidence_score=0.90,
        completeness_score=1.0,
    )
    adapter.update_edge(
        edge["edge_id"], response_id=resp["response_id"], status="APPROVED",
    )
    adapter.create_rollup(
        project_id=project["project_id"],
        main_supplier_actor_id=supplier["actor_id"],
        can_accept_order=True, completeness_score=1.0, confidence_score=0.90,
    )
    for ev_type, payload in [
        ("ORDER_CONFIRMED",  {"milestone": "order_placed"}),
        ("PRODUCTION_UPDATE_RECEIVED", {"milestone": "cutting", "pct": 40}),
        ("QC_UPDATE_RECEIVED", {"result": "pass", "defect_rate": 0.003}),
        ("LOGISTICS_HANDOVER_RECEIVED", {"tracking": "DHL123456789"}),
        ("ORDER_CLOSED", {"status": "closed_ok"}),
    ]:
        adapter.log_event(
            event_type=ev_type,
            project_id=project["project_id"],
            actor_id=supplier["actor_id"],
            edge_id=edge["edge_id"],
            payload_json=payload,
        )
    return {
        "project_id": project["project_id"],
        "edge_id": edge["edge_id"],
        "inquiry_id": inq["inquiry_id"],
        "response_id": resp["response_id"],
        "requirement_id": req["requirement_id"],
        "buyer_id": buyer["actor_id"],
        "supplier_id": supplier["actor_id"],
    }


# ===========================================================================
# Regression Guard — v1.0 Baseline
# ===========================================================================

def suite_baseline_regression(db_url: str) -> SuiteResult:
    suite = SuiteResult("Baseline v1.0 Regression (verify_integration --runs 5)", True)
    _banner(suite.name)
    try:
        result = subprocess.run(
            [sys.executable, "verify_integration.py", "--db", db_url, "--runs", "5"],
            capture_output=True, text=True, cwd=_ROOT,
        )
        for line in result.stdout.splitlines():
            print(f"    {line}")
        if result.returncode != 0:
            raise _fail(suite, "verify_integration.py returned non-zero exit code")
        if "5/5 passed" not in result.stdout:
            raise _fail(suite, "verify_integration did not report 5/5 passed")
        _pass(suite, "verify_integration 5/5 passed")
    except AssertionError:
        pass
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Regression Guard — v1.1 Hardening
# ===========================================================================

def suite_v11_hardening_regression(db_url: str) -> SuiteResult:
    suite = SuiteResult("v1.1 Hardening Regression (bm_db_hardening --db)", True)
    _banner(suite.name)
    try:
        result = subprocess.run(
            [sys.executable, "bm_db_hardening.py", "--db", db_url],
            capture_output=True, text=True, cwd=_ROOT,
        )
        for line in result.stdout.splitlines():
            print(f"    {line}")
        if result.returncode != 0:
            raise _fail(suite, "bm_db_hardening.py returned non-zero exit code")
        if "8/8 suites passed" not in result.stdout:
            raise _fail(suite, "hardening did not report 8/8 suites passed")
        _pass(suite, "hardening 8/8 suites passed")
    except AssertionError:
        pass
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Regression Guard — v1.2 Replay + Decision Packet
# ===========================================================================

def suite_v12_replay_regression(db_url: str) -> SuiteResult:
    suite = SuiteResult("v1.2 Replay + Decision Packet Regression", True)
    _banner(suite.name)
    try:
        result = subprocess.run(
            [sys.executable, "bm_db_v12_replay_test.py", "--db", db_url],
            capture_output=True, text=True, cwd=_ROOT,
        )
        for line in result.stdout.splitlines():
            print(f"    {line}")
        if result.returncode != 0:
            raise _fail(suite, "bm_db_v12_replay_test.py returned non-zero exit code")
        if "4/4 suites passed" not in result.stdout:
            raise _fail(suite, "v1.2 test did not report 4/4 suites passed")
        _pass(suite, "v1.2 replay tests 4/4 passed")
    except AssertionError:
        pass
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Suite T1 — Rule Packet Registry
# ===========================================================================

def suite_rule_packet_registry() -> SuiteResult:
    suite = SuiteResult("T1. Rule Packet Registry", True)
    _banner(suite.name)
    try:
        from rule_packet_registry import (
            RulePacketRegistry, RulePacketError, verify_rule_hash, registry,
        )

        # All 7 packets available and hash-verified
        active = registry.list_active()
        assert len(active) == 7, f"expected 7 active packets, got {len(active)}"
        _pass(suite, f"list_active() returned {len(active)} packets")

        expected_types = [
            "buyer_requirement", "supplier_inquiry",
            "supplier_response_normalization", "feasibility_scoring",
            "decision_packet_generation", "order_confirmation",
            "production_qc_logistics",
        ]
        active_types = {p["rule_packet_type"] for p in active}
        for t in expected_types:
            assert t in active_types, f"missing packet type: {t}"
        _pass(suite, "all 7 expected packet types present")

        # Hash integrity for each
        for t in expected_types:
            packet = registry.get(t, "1.0")
            assert verify_rule_hash(packet), f"hash mismatch for {t}"
        _pass(suite, "all 7 packets hash-verified")

        # Unknown type raises
        try:
            registry.get("nonexistent_type", "1.0")
            raise _fail(suite, "should have raised RulePacketError for missing type")
        except RulePacketError:
            _pass(suite, "RulePacketError raised for missing rule type")

        # get_by_id round-trips correctly
        packet = registry.get("buyer_requirement", "1.0")
        pid = packet["rule_packet_id"]
        packet2 = registry.get_by_id(pid)
        assert packet2["rule_packet_type"] == "buyer_requirement"
        _pass(suite, f"get_by_id round-trip OK for buyer_requirement (id={pid[:8]}…)")

        # assert_hash_stable passes for all
        for t in expected_types:
            registry.assert_hash_stable(t, "1.0")
        _pass(suite, "assert_hash_stable passed for all 7 packets")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Suite T2 — Evidence Guard
# ===========================================================================

def suite_evidence_guard(db_url: str) -> SuiteResult:
    suite = SuiteResult("T2. Evidence Guard", True)
    _banner(suite.name)
    try:
        from evidence_guard import check_response, check_many, EvidenceGuardResult

        # Clean response — no flags
        clean = {
            "response_id": "r-clean",
            "can_supply": True,
            "price": 8.50,
            "currency": "USD",
            "moq": 100,
            "lead_time_days": 30,
            "available_quantity": 500,
        }
        result = check_response(clean)
        assert result.is_clean, f"clean response should pass: {result.risk_flags}"
        assert not result.requires_human_confirmation
        _pass(suite, "clean response passes evidence guard")

        # Placeholder value forbidden — price=999
        bad_placeholder = {**clean, "response_id": "r-ph", "price": 999}
        result = check_response(bad_placeholder)
        assert not result.is_clean, "placeholder value should be flagged"
        assert any("placeholder" in f.lower() for f in result.risk_flags)
        assert result.requires_human_confirmation
        _pass(suite, "placeholder value price=999 correctly flagged")

        # can_supply=True, price=None → missing commercial field
        missing_price = {
            "response_id": "r-mp",
            "can_supply": True,
            "price": None,
            "currency": "USD",
            "moq": 100,
            "lead_time_days": 30,
        }
        result = check_response(missing_price)
        assert not result.is_clean, "missing price with can_supply=True should be flagged"
        assert any("missing" in f.lower() or "price" in f.lower() for f in result.risk_flags)
        _pass(suite, "can_supply=True + price=None correctly flagged")

        # ai_inferred without risk flag — should raise source violation
        field_sources = {"price": "ai_inferred"}
        result = check_response(
            {**clean, "response_id": "r-inf", "risk_flags_json": {}},
            field_sources=field_sources,
        )
        assert not result.is_clean, "ai_inferred without risk flag should be flagged"
        assert any("source_violation" in f for f in result.risk_flags)
        _pass(suite, "ai_inferred price without risk flag correctly flagged")

        # ai_inferred WITH risk flag — should pass source check
        field_sources_ok = {"price": "ai_inferred"}
        result = check_response(
            {**clean, "response_id": "r-inf-ok",
             "risk_flags_json": {"price": "ai_inferred_value"}},
            field_sources=field_sources_ok,
        )
        # Note: can_supply=True + valid price is still clean
        assert result.is_clean or all("source_violation" not in f for f in result.risk_flags), \
            "ai_inferred with risk flag should not trigger source_violation"
        _pass(suite, "ai_inferred with risk flag does not trigger source_violation")

        # check_many on a batch
        responses = [clean, missing_price, bad_placeholder]
        many = check_many(responses)
        assert len(many) == 3, f"check_many should return 3 results, got {len(many)}"
        _pass(suite, f"check_many returned {len(many)} results correctly")

        # source=missing but value present — inconsistency
        inconsistent = {**clean, "response_id": "r-inc"}
        result_inc = check_response(
            inconsistent,
            field_sources={"price": "missing"},
        )
        assert not result_inc.is_clean, "source=missing with non-None value should be flagged"
        assert any("source_violation" in f for f in result_inc.risk_flags)
        _pass(suite, "source=missing with non-None value correctly flagged")

        # DB-mode evidence gap event logging
        with _adapter(db_url) as adapter:
            ids = _build_lifecycle(adapter, f"eg-{uuid.uuid4().hex[:4]}")
            c0 = adapter.get_counts()

            result_gap = check_response(
                {**bad_placeholder, "edge_id": ids["edge_id"]},
                adapter=adapter,
                project_id=ids["project_id"],
                edge_id=ids["edge_id"],
                actor_id=ids["supplier_id"],
            )
            c1 = adapter.get_counts()

        assert not result_gap.is_clean
        assert c1.get("execution_events", 0) > c0.get("execution_events", 0), \
            "AI_OUTPUT_EVIDENCE_GAP event not written to DB"
        _pass(suite, "AI_OUTPUT_EVIDENCE_GAP event written to DB for placeholder violation")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Suite T3 — Human Confirmation
# ===========================================================================

def suite_human_confirmation(db_url: str) -> SuiteResult:
    suite = SuiteResult("T3. Human Confirmation & Override Detection", True)
    _banner(suite.name)
    try:
        from human_confirmation import (
            request_confirmation, record_confirmation,
            assert_confirmation_required, ConfirmationResult,
            EVENT_REQUIRED, EVENT_RECEIVED, EVENT_OVERRIDE,
        )
        with _adapter(db_url) as adapter:
            ids = _build_lifecycle(adapter, f"hc-{uuid.uuid4().hex[:4]}")

            supplier_response = {
                "response_id": ids["response_id"],
                "price": 7.20,
                "currency": "USD",
                "lead_time_days": 25,
                "quantity": 200,
            }

            c0 = adapter.get_counts()

            # request_confirmation writes HUMAN_CONFIRMATION_REQUIRED event
            eid_req = request_confirmation(
                project_id=ids["project_id"],
                edge_id=ids["edge_id"],
                actor_id=ids["buyer_id"],
                response_summary=supplier_response,
                adapter=adapter,
            )
            c1 = adapter.get_counts()
            assert c1.get("execution_events", 0) > c0.get("execution_events", 0)
            _pass(suite, f"HUMAN_CONFIRMATION_REQUIRED event written (event_id={str(eid_req)[:8]}…)")

            # Full confirmation — no overrides, edge approved
            confirmed = {
                "selected_supplier_actor_id": ids["supplier_id"],
                "confirmed_price": 7.20,
                "confirmed_currency": "USD",
                "confirmed_lead_time_days": 25,
                "confirmed_quantity": 200,
            }
            result = record_confirmation(
                project_id=ids["project_id"],
                edge_id=ids["edge_id"],
                confirming_actor_id=ids["buyer_id"],
                confirmed=confirmed,
                supplier_response=supplier_response,
                adapter=adapter,
            )
            assert result.is_confirmed, f"confirmation should be complete: missing={result.missing_fields}"
            assert len(result.overrides) == 0, f"no overrides expected: {result.overrides}"
            assert result.edge_approved, "edge should be approved after confirmation"
            _pass(suite, "full confirmation: is_confirmed=True, no overrides, edge APPROVED")

            # Override detection — buyer changes price
            c2 = adapter.get_counts()
            confirmed_override = {**confirmed, "confirmed_price": 6.50}
            ids2 = _build_lifecycle(adapter, f"hc-ov-{uuid.uuid4().hex[:4]}")
            resp2 = {"response_id": ids2["response_id"], "price": 7.20, "currency": "USD",
                     "lead_time_days": 25, "quantity": 200}
            result_ov = record_confirmation(
                project_id=ids2["project_id"],
                edge_id=ids2["edge_id"],
                confirming_actor_id=ids2["buyer_id"],
                confirmed=confirmed_override,
                supplier_response=resp2,
                adapter=adapter,
            )
            c3 = adapter.get_counts()
            assert result_ov.is_confirmed, "override confirmation should still be complete"
            assert len(result_ov.overrides) == 1, \
                f"expected 1 override for price, got: {result_ov.overrides}"
            assert result_ov.overrides[0]["field"] == "confirmed_price"
            assert result_ov.overrides[0]["supplier_stated"] == 7.20
            assert result_ov.overrides[0]["human_confirmed"] == 6.50
            # Two events should have been written: RECEIVED + OVERRIDE
            assert c3.get("execution_events", 0) >= c2.get("execution_events", 0) + 2, \
                "expected at least HUMAN_CONFIRMATION_RECEIVED + HUMAN_OVERRIDE_DETECTED events"
            _pass(suite, "override detected: price 7.20→6.50; HUMAN_OVERRIDE_DETECTED event written")

            # Missing confirmation fields
            partial = {"selected_supplier_actor_id": ids["supplier_id"], "confirmed_price": 7.20}
            result_partial = record_confirmation(
                project_id=ids["project_id"],
                edge_id=ids["edge_id"],
                confirming_actor_id=ids["buyer_id"],
                confirmed=partial,
                supplier_response=supplier_response,
                adapter=adapter,
            )
            assert not result_partial.is_confirmed, "partial confirmation should not be confirmed"
            assert len(result_partial.missing_fields) >= 3, \
                f"expected 3+ missing fields: {result_partial.missing_fields}"
            _pass(suite, f"partial confirmation correctly rejected: missing={result_partial.missing_fields}")

        # assert_confirmation_required passes for compliant packet
        good_packet = {"human_confirmation_required": True, "project_id": "x"}
        assert_confirmation_required(good_packet)
        _pass(suite, "assert_confirmation_required passes for compliant packet")

        # assert_confirmation_required raises for non-compliant
        try:
            assert_confirmation_required({"human_confirmation_required": False})
            raise _fail(suite, "should have raised ValueError")
        except ValueError:
            _pass(suite, "assert_confirmation_required raises for False")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Suite T4 — Rule Packet + Evidence Guard Integration (with adapter)
# ===========================================================================

def suite_rule_packet_evidence_integration(db_url: str) -> SuiteResult:
    suite = SuiteResult("T4. Rule Packet + Evidence Guard Integration", True)
    _banner(suite.name)
    try:
        from rule_packet_registry import registry
        from evidence_guard import check_response

        # Load supplier_response_normalization rule packet and verify its rules are applied
        packet = registry.get("supplier_response_normalization", "1.0")
        assert packet["status"] == "active"
        forbidden = packet["rule_content_json"].get("placeholder_values_forbidden", [])
        assert 999 in forbidden, "rule packet must forbid 999"
        _pass(suite, f"supplier_response_normalization rule packet active; forbidden={forbidden}")

        # Use the rule's commercial_fields list to construct a response
        commercial_fields = packet["rule_content_json"]["commercial_fields"]
        resp = {f: None for f in commercial_fields}
        resp.update({
            "response_id": "r-integration",
            "can_supply": True,
            "price": 999,      # forbidden placeholder per the rule packet
            "currency": "USD",
        })
        result = check_response(resp)
        assert not result.is_clean, "rule-forbidden placeholder should be flagged"
        _pass(suite, "evidence guard correctly flags placeholder value from rule packet definition")

        # Verify all 7 rule packets are hash-stable
        all_types = [p["rule_packet_type"] for p in registry.list_active()]
        for t in all_types:
            registry.assert_hash_stable(t, "1.0")
        _pass(suite, f"all {len(all_types)} rule packets hash-stable in integrated check")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Suite T5 — Five-run Reproducibility (v1.3 full stack)
# ===========================================================================

def suite_five_run_v13(db_url: str) -> SuiteResult:
    suite = SuiteResult("T5. Five-run Reproducibility (v1.3 full stack)", True)
    _banner(suite.name)
    run_results = []
    try:
        from evidence_guard import check_response
        from human_confirmation import record_confirmation
        from rule_packet_registry import registry, verify_rule_hash
        import bm_db_adapter as bma
        import execution_graph_replay as egr
        import decision_packet_generator as dpg

        for run in range(1, 6):
            run_ok = True
            with _adapter(db_url) as adapter:
                ids = _build_lifecycle(adapter, f"v13-run{run}-{uuid.uuid4().hex[:4]}")

                # Check evidence guard on the response
                resp_dict = {
                    "response_id": ids["response_id"],
                    "can_supply": True,
                    "price": 7.20,
                    "currency": "USD",
                    "moq": 50,
                    "lead_time_days": 25,
                }
                guard_result = check_response(resp_dict)
                if not guard_result.is_clean:
                    run_ok = False

                # Confirm the order
                confirm_result = record_confirmation(
                    project_id=ids["project_id"],
                    edge_id=ids["edge_id"],
                    confirming_actor_id=ids["buyer_id"],
                    confirmed={
                        "selected_supplier_actor_id": ids["supplier_id"],
                        "confirmed_price": 7.20,
                        "confirmed_currency": "USD",
                        "confirmed_lead_time_days": 25,
                        "confirmed_quantity": 200,
                    },
                    supplier_response=resp_dict,
                    adapter=adapter,
                )
                if not confirm_result.is_confirmed:
                    run_ok = False

            # Replay and packet (adapter already closed by context manager)
            graph = egr.replay_project(db_url, ids["project_id"])
            packet = dpg.generate_packet(db_url, ids["project_id"])
            if "error" in graph or "error" in packet:
                run_ok = False
            if not packet.get("human_confirmation_required"):
                run_ok = False

            # Rule hashes stable
            for t in ["buyer_requirement", "supplier_response_normalization", "order_confirmation"]:
                if not verify_rule_hash(registry.get(t, "1.0")):
                    run_ok = False

            run_results.append(run_ok)
            status = "PASS" if run_ok else "FAIL"
            print(f"    run {run}/5: {status}  (project={ids['project_id'][:8]}…)")

        passed = sum(run_results)
        assert passed == 5, f"only {passed}/5 runs passed"
        _pass(suite, "5/5 reproducibility runs passed (v1.3 full stack)")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ===========================================================================
# Sample artifact generation
# ===========================================================================

def _generate_v13_samples(db_url: str, output_dir: str) -> None:
    from rule_packet_registry import registry
    from human_confirmation import (
        request_confirmation, record_confirmation,
        EVENT_RECEIVED, EVENT_OVERRIDE,
    )
    import decision_packet_generator as dpg

    # 1. sample_rule_packet.json (no DB needed)
    rp = registry.get("supplier_response_normalization", "1.0")
    with open(os.path.join(output_dir, "sample_rule_packet.json"), "w") as fh:
        json.dump(rp, fh, indent=2, default=str)

    # Lifecycle for confirmation and override samples
    with _adapter(db_url) as adapter:
        ids = _build_lifecycle(adapter, "v13-sample")

        supplier_response = {
            "response_id": ids["response_id"],
            "price": 7.20,
            "currency": "USD",
            "lead_time_days": 25,
            "quantity": 200,
        }

        # 2. sample_human_confirmation_event.json
        request_confirmation(
            project_id=ids["project_id"],
            edge_id=ids["edge_id"],
            actor_id=ids["buyer_id"],
            response_summary=supplier_response,
            adapter=adapter,
        )
        confirm_result = record_confirmation(
            project_id=ids["project_id"],
            edge_id=ids["edge_id"],
            confirming_actor_id=ids["buyer_id"],
            confirmed={
                "selected_supplier_actor_id": ids["supplier_id"],
                "confirmed_price": 7.20,
                "confirmed_currency": "USD",
                "confirmed_lead_time_days": 25,
                "confirmed_quantity": 200,
            },
            supplier_response=supplier_response,
            adapter=adapter,
        )
        hc_sample = {
            "event_type": EVENT_RECEIVED,
            "project_id": ids["project_id"],
            "edge_id": ids["edge_id"],
            "confirming_actor_id": ids["buyer_id"],
            "is_confirmed": confirm_result.is_confirmed,
            "overrides": confirm_result.overrides,
            "events_written": confirm_result.events_written,
            "edge_approved": confirm_result.edge_approved,
        }
        with open(os.path.join(output_dir, "sample_human_confirmation_event.json"), "w") as fh:
            json.dump(hc_sample, fh, indent=2, default=str)

        # 3. sample_override_detection_event.json
        ids3 = _build_lifecycle(adapter, "v13-override-sample")
        resp3 = {
            "response_id": ids3["response_id"],
            "price": 7.20, "currency": "USD", "lead_time_days": 25, "quantity": 200,
        }
        result_ov = record_confirmation(
            project_id=ids3["project_id"],
            edge_id=ids3["edge_id"],
            confirming_actor_id=ids3["buyer_id"],
            confirmed={
                "selected_supplier_actor_id": ids3["supplier_id"],
                "confirmed_price": 6.00,   # override
                "confirmed_currency": "USD",
                "confirmed_lead_time_days": 25,
                "confirmed_quantity": 200,
            },
            supplier_response=resp3,
            adapter=adapter,
        )
        override_sample = {
            "event_type": EVENT_OVERRIDE,
            "project_id": ids3["project_id"],
            "edge_id": ids3["edge_id"],
            "overrides": result_ov.overrides,
            "events_written": result_ov.events_written,
        }
        with open(os.path.join(output_dir, "sample_override_detection_event.json"), "w") as fh:
            json.dump(override_sample, fh, indent=2, default=str)

        sample_project_id = ids["project_id"]

    # 4. sample_decision_packet_with_evidence.md (separate adapter)
    packet = dpg.generate_packet(db_url, sample_project_id)
    md = dpg._render_packet_markdown(packet)
    rp_version_note = (
        f"\n> **Rule Packet:** `supplier_response_normalization` v{rp['version']} "
        f"(hash: `{rp['rule_hash'][:16]}…`)\n"
    )
    md_with_evidence = md.replace("## 1. RFQ Summary", rp_version_note + "## 1. RFQ Summary")
    with open(
        os.path.join(output_dir, "sample_decision_packet_with_evidence.md"), "w"
    ) as fh:
        fh.write(md_with_evidence)


# ===========================================================================
# Main
# ===========================================================================

def main(db_url: str, output_dir: str = ".") -> bool:
    print("=" * 70)
    print("BM DB Integration — v1.3 Trust Boundary & Rule Integrity Test Suite")
    print(f"DB: {db_url}")
    print("=" * 70)

    suites: List[SuiteResult] = []

    # Regression guards first
    suites.append(suite_baseline_regression(db_url))
    suites.append(suite_v11_hardening_regression(db_url))
    suites.append(suite_v12_replay_regression(db_url))

    # v1.3 trust suites
    suites.append(suite_rule_packet_registry())
    suites.append(suite_evidence_guard(db_url))
    suites.append(suite_human_confirmation(db_url))
    suites.append(suite_rule_packet_evidence_integration(db_url))
    suites.append(suite_five_run_v13(db_url))

    # Sample artifacts
    print("\n--- Generating v1.3 sample artifacts ---")
    try:
        _generate_v13_samples(db_url, output_dir)
        for fname in [
            "sample_rule_packet.json",
            "sample_human_confirmation_event.json",
            "sample_override_detection_event.json",
            "sample_decision_packet_with_evidence.md",
        ]:
            path = os.path.join(output_dir, fname)
            if os.path.exists(path):
                print(f"    written: {path}")
    except Exception as exc:
        print(f"    WARN: sample generation failed: {exc}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_passed = True
    for s in suites:
        mark = "✓" if s.passed else "✗"
        print(f"  {mark}  {s.name}")
        if not s.passed:
            all_passed = False
            for err in s.errors:
                print(f"       ERROR: {err}")

    passed_count = sum(1 for s in suites if s.passed)
    print(f"\n  {passed_count}/{len(suites)} suites passed")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=os.environ.get("GIRAFFE_DB_URL", "sqlite:///./v13_test.db"),
    )
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    import build_schema
    build_schema.build(args.db)

    ok = main(args.db, args.output_dir)
    sys.exit(0 if ok else 1)
