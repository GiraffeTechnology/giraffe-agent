"""BM DB Integration v1.2 — Execution Graph Replay + Decision Packet test suite.

Runs 5 independent lifecycle runs, testing:
  1. replay_project output shape and content
  2. generate_packet output shape, evidence rules, human_confirmation_required
  3. Markdown rendering for both modules
  4. Five-run reproducibility on a fresh DB
  5. sample artifact generation

Usage::

    python bm_db_v12_replay_test.py --db sqlite:///./v12_test.db
"""

from __future__ import annotations

import json
import os
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
# Lifecycle builder
# ---------------------------------------------------------------------------

def _build_lifecycle(adapter: Any, run_label: str) -> dict:
    """Create a full single-supplier lifecycle and return key IDs."""
    buyer = adapter.get_or_create_actor(
        f"V12 Buyer {run_label}", "BUYER",
        default_language="en", is_active=True,
    )
    supplier = adapter.get_or_create_actor(
        f"V12 Supplier {run_label}", "SUPPLIER",
        default_language="zh", is_active=True,
    )

    project = adapter.get_or_create_project(
        original_buyer_actor_id=buyer["actor_id"],
        project_key=f"v12-polo-shirts-{run_label}",
        main_supplier_actor_id=supplier["actor_id"],
    )

    req = adapter.create_requirement(
        project_id=project["project_id"],
        source_actor_id=buyer["actor_id"],
        category="Apparel",
        quantity=300,
        material="Cotton",
        deadline="2026-09-30",
        destination="New York",
        confidence_score=0.91,
    )

    edge = adapter.create_edge(
        project_id=project["project_id"],
        from_actor_id=buyer["actor_id"],
        to_actor_id=supplier["actor_id"],
        edge_type="MAIN_B_TO_M",
        status="PENDING",
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
        price=8.50,
        currency="USD",
        moq=100,
        lead_time_days=30,
        available_quantity=500,
        confidence_score=0.88,
        completeness_score=1.0,
    )

    adapter.update_edge(
        edge["edge_id"],
        response_id=resp["response_id"],
        status="APPROVED",
    )

    adapter.create_rollup(
        project_id=project["project_id"],
        main_supplier_actor_id=supplier["actor_id"],
        can_accept_order=True,
        completeness_score=1.0,
        confidence_score=0.88,
    )

    for ev_type, payload in [
        ("ORDER_CONFIRMED", {"milestone": "order_placed"}),
        ("PRODUCTION_UPDATE_RECEIVED", {"milestone": "cutting_started", "pct": 25}),
        ("QC_UPDATE_RECEIVED", {"result": "pass", "defect_rate": 0.005}),
        ("LOGISTICS_HANDOVER_RECEIVED", {"tracking": "SF9876543210"}),
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


# ---------------------------------------------------------------------------
# Suite 1 — replay_project output shape
# ---------------------------------------------------------------------------

def suite_replay_shape(db_url: str) -> SuiteResult:
    suite = SuiteResult("1. Execution Graph Replay — Output Shape", True)
    _banner(suite.name)
    try:
        with _adapter(db_url) as adapter:
            ids = _build_lifecycle(adapter, f"replay-shape-{uuid.uuid4().hex[:6]}")

        import execution_graph_replay as egr
        graph = egr.replay_project(db_url, ids["project_id"])

        if "error" in graph:
            raise _fail(suite, f"replay returned error: {graph['error']}")

        for key in ("project_id", "buyer", "structured_requirement",
                    "inquiries", "responses", "selected_edge",
                    "execution_events", "event_timeline"):
            if key not in graph:
                raise _fail(suite, f"missing key in replay output: {key!r}")
        _pass(suite, "replay output has all required keys")

        assert graph["project_id"] == ids["project_id"]
        _pass(suite, f"project_id matches: {ids['project_id'][:8]}…")

        assert len(graph["inquiries"]) >= 1, "no inquiries in replay"
        _pass(suite, f"inquiries: {len(graph['inquiries'])}")

        assert len(graph["responses"]) >= 1, "no responses in replay"
        _pass(suite, f"responses: {len(graph['responses'])}")

        assert len(graph["execution_events"]) >= 5, "fewer than 5 events in replay"
        _pass(suite, f"execution_events: {len(graph['execution_events'])}")

        timeline = graph["event_timeline"]
        assert any("ORDER_CONFIRMED" in t for t in timeline), "ORDER_CONFIRMED missing from timeline"
        assert any("ORDER_CLOSED" in t for t in timeline), "ORDER_CLOSED missing from timeline"
        _pass(suite, f"timeline has ORDER_CONFIRMED → ORDER_CLOSED ({len(timeline)} entries)")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ---------------------------------------------------------------------------
# Suite 2 — generate_packet output shape + evidence rules
# ---------------------------------------------------------------------------

def suite_decision_packet_shape(db_url: str) -> SuiteResult:
    suite = SuiteResult("2. Decision Packet — Output Shape + Evidence Rules", True)
    _banner(suite.name)
    try:
        with _adapter(db_url) as adapter:
            ids = _build_lifecycle(adapter, f"dp-shape-{uuid.uuid4().hex[:6]}")

        import decision_packet_generator as dpg
        packet = dpg.generate_packet(db_url, ids["project_id"])

        if "error" in packet:
            raise _fail(suite, f"generate_packet returned error: {packet['error']}")

        for key in ("project_id", "rfq_summary", "supplier_comparison",
                    "top_3_options", "recommended_option", "risk_flags",
                    "missing_fields", "human_confirmation_required",
                    "confirmation_note", "generated_at"):
            if key not in packet:
                raise _fail(suite, f"missing key in packet: {key!r}")
        _pass(suite, "packet has all required keys")

        assert packet["human_confirmation_required"] is True, \
            "human_confirmation_required must be True"
        _pass(suite, "human_confirmation_required=True")

        assert "NOT" in packet["confirmation_note"] or \
               "not" in packet["confirmation_note"].lower(), \
            "confirmation_note does not warn about limitations"
        _pass(suite, "confirmation_note contains required disclaimer")

        rec = packet["recommended_option"]
        if rec.get("status") == "recommended":
            assert rec.get("response_id"), "recommended_option missing response_id"
            assert rec.get("evidence_note"), "recommended_option missing evidence_note"
            _pass(suite, f"recommended option: price={rec.get('price')} currency={rec.get('currency')}")
        else:
            _pass(suite, f"recommended_option status={rec.get('status')!r} (acceptable)")

        comparisons = packet["supplier_comparison"]
        assert len(comparisons) >= 1, "no supplier_comparison rows"
        for row in comparisons:
            assert row.get("response_id"), "comparison row missing response_id"
        _pass(suite, f"supplier_comparison rows: {len(comparisons)}")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ---------------------------------------------------------------------------
# Suite 3 — Markdown rendering
# ---------------------------------------------------------------------------

def suite_markdown_rendering(db_url: str) -> SuiteResult:
    suite = SuiteResult("3. Markdown Rendering", True)
    _banner(suite.name)
    try:
        with _adapter(db_url) as adapter:
            ids = _build_lifecycle(adapter, f"md-{uuid.uuid4().hex[:6]}")

        import execution_graph_replay as egr
        import decision_packet_generator as dpg

        graph = egr.replay_project(db_url, ids["project_id"])
        md_graph = egr._render_markdown(graph)
        assert "# Execution Graph" in md_graph, "replay markdown missing H1 heading"
        assert ids["project_id"][:8] in md_graph, "project_id not in replay markdown"
        _pass(suite, f"replay markdown: {len(md_graph)} chars, heading present")

        packet = dpg.generate_packet(db_url, ids["project_id"])
        md_packet = dpg._render_packet_markdown(packet)
        assert "# Decision Packet" in md_packet, "packet markdown missing H1 heading"
        assert "HUMAN CONFIRMATION REQUIRED" in md_packet, \
            "packet markdown missing human confirmation banner"
        _pass(suite, f"decision packet markdown: {len(md_packet)} chars, banner present")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ---------------------------------------------------------------------------
# Suite 4 — Five-run reproducibility
# ---------------------------------------------------------------------------

def suite_five_run(db_url: str) -> SuiteResult:
    suite = SuiteResult("4. Five-run Reproducibility", True)
    _banner(suite.name)
    run_results = []
    try:
        import execution_graph_replay as egr
        import decision_packet_generator as dpg

        for run in range(1, 6):
            with _adapter(db_url) as adapter:
                ids = _build_lifecycle(adapter, f"repro-run{run}-{uuid.uuid4().hex[:4]}")

            graph = egr.replay_project(db_url, ids["project_id"])
            packet = dpg.generate_packet(db_url, ids["project_id"])

            ok = (
                graph.get("project_id") == ids["project_id"]
                and "buyer" in graph
                and "error" not in packet
                and packet.get("human_confirmation_required") is True
                and len(graph.get("execution_events", [])) >= 5
            )
            run_results.append(ok)
            status = "PASS" if ok else "FAIL"
            print(f"    run {run}/5: {status}  (project={ids['project_id'][:8]}…)")

        passed = sum(run_results)
        assert passed == 5, f"only {passed}/5 runs passed"
        _pass(suite, "5/5 reproducibility runs passed")

    except AssertionError as exc:
        if suite.passed:
            _fail(suite, str(exc))
    except Exception as exc:
        _fail(suite, f"unexpected error: {exc}")
    print(f"  → {'PASS' if suite.passed else 'FAIL'}")
    return suite


# ---------------------------------------------------------------------------
# Sample artifact generation
# ---------------------------------------------------------------------------

def _generate_samples(db_url: str, output_dir: str) -> None:
    with _adapter(db_url) as adapter:
        ids = _build_lifecycle(adapter, "sample")

    import execution_graph_replay as egr
    import decision_packet_generator as dpg

    graph = egr.replay_project(db_url, ids["project_id"])
    packet = dpg.generate_packet(db_url, ids["project_id"])
    md_graph = egr._render_markdown(graph)
    md_packet = dpg._render_packet_markdown(packet)

    samples = {
        "sample_execution_graph.json": json.dumps(graph, indent=2, default=str),
        "sample_execution_graph.md": md_graph,
        "sample_decision_packet.json": json.dumps(packet, indent=2, default=str),
        "sample_decision_packet.md": md_packet,
    }
    for fname, content in samples.items():
        path = os.path.join(output_dir, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"    written: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(db_url: str, output_dir: str = ".") -> bool:
    print("=" * 66)
    print("BM DB Integration — v1.2 Replay + Decision Packet Test Suite")
    print(f"DB: {db_url}")
    print("=" * 66)

    suites = [
        suite_replay_shape(db_url),
        suite_decision_packet_shape(db_url),
        suite_markdown_rendering(db_url),
        suite_five_run(db_url),
    ]

    # Generate sample artifacts
    print("\n--- Generating sample artifacts ---")
    try:
        _generate_samples(db_url, output_dir)
    except Exception as exc:
        print(f"    WARN: sample generation failed: {exc}")

    # Summary
    print("\n" + "=" * 66)
    print("SUMMARY")
    print("=" * 66)
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
    print("=" * 66)
    return all_passed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=os.environ.get("GIRAFFE_DB_URL", "sqlite:///./v12_test.db"),
    )
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    import build_schema
    build_schema.build(args.db)

    ok = main(args.db, args.output_dir)
    sys.exit(0 if ok else 1)
