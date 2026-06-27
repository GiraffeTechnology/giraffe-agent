"""Faithful in-memory fake of the standalone GLTG HTTP API for tests/CI.

`route()` is a pure function (no httpx) that maps an endpoint + JSON body to a
(status, body) pair, mirroring the GLTG service deterministically. It is used
both by `mock_transport()` (httpx.MockTransport, for unit tests) and by
`tests/ci_gltg_server.py` (a real stdlib HTTP server, for CI E2E scripts).

This is test/CI infrastructure only -- it is NOT product code and NOT a runtime
fallback. Production always talks to the real standalone GLTG service.
"""

from __future__ import annotations

import json
import math
from datetime import date, timedelta


def _baseline_total(quantity: int, supplier: dict) -> float:
    stage = (
        (supplier.get("material_ready_days") or 0)
        + (supplier.get("production_days") or 0)
        + (supplier.get("qc_days") or 0)
        + (supplier.get("logistics_days") or 0)
    )
    if stage > 0:
        cap = supplier.get("capacity_per_day") or 0
        if cap and quantity:
            stage = max(stage, math.ceil(quantity / cap))
        return float(stage)
    cap = supplier.get("capacity_per_day") or 500
    production = max(math.ceil(quantity / max(int(cap * 0.85), 1)), 1) + 2
    return float(17 + production + 6 + 30)


def _effective_deadline(order: dict) -> int | None:
    if order.get("deadline_days") is not None:
        return int(order["deadline_days"])
    return None


def _estimate(payload: dict) -> dict:
    order = payload.get("order", {})
    suppliers = payload.get("suppliers", []) or []
    quantity = order.get("quantity", 0) or 0
    deadline = _effective_deadline(order)
    n = len(suppliers)
    warnings: list[dict] = []
    if n == 0:
        return {
            "status": "ok",
            "estimated_lead_time_days": None,
            "earliest_delivery_date": None,
            "feasible": False,
            "supplier_count": 0,
            "selected_supplier_id": None,
            "p50_days": None,
            "p80_days": None,
            "p90_days": None,
            "minimum_feasible_days": None,
            "risk_level": "unknown",
            "warnings": [{"code": "NO_SUPPLIERS", "message": "No suppliers provided."}],
            "calculation_trace": [],
        }
    traces = []
    totals = []
    for s in suppliers:
        total = _baseline_total(quantity, s)
        totals.append((total, s))
        traces.append(
            {
                "supplier_id": s.get("supplier_id", "?"),
                "material_ready_days": s.get("material_ready_days") or 17,
                "production_days": s.get("production_days") or 0,
                "capacity_adjusted_production_days": s.get("production_days")
                or (max(math.ceil(quantity / max(int((s.get("capacity_per_day") or 500) * 0.85), 1)), 1) + 2),
                "qc_days": s.get("qc_days") or 6,
                "logistics_days": s.get("logistics_days") or 30,
                "total_lead_time_days": total,
                "confidence": s.get("confidence", 0.5),
                "feasible": deadline is None or total <= deadline,
            }
        )
    totals.sort(key=lambda t: t[0])
    total, selected = totals[0]
    conf = selected.get("confidence", 0.5)
    p50 = float(round(total))
    p80 = float(math.ceil(total * (1.10 + 0.20 * (1 - conf))))
    p90 = float(math.ceil(total * (1.20 + 0.35 * (1 - conf))))
    minimum = float(math.floor(total * 0.85))
    feasible = deadline is None or total <= deadline
    if deadline is None:
        risk = "low" if conf >= 0.75 else "medium" if conf >= 0.5 else "high"
    elif total > deadline:
        risk = "high"
    elif p80 > deadline:
        risk = "medium"
    else:
        risk = "low"
    if n == 1:
        warnings.append({"code": "LIMITED_COMPARISON", "message": "one supplier"})
    elif n == 2:
        warnings.append({"code": "LIMITED_SUPPLIER_POOL", "message": "two suppliers"})
    if not feasible and deadline is not None:
        warnings.append({"code": "TARGET_NOT_MET", "message": "deadline not met"})
    earliest = (date.today() + timedelta(days=int(math.ceil(total)))).isoformat()
    return {
        "status": "ok",
        "estimated_lead_time_days": total,
        "earliest_delivery_date": earliest,
        "feasible": feasible,
        "supplier_count": n,
        "selected_supplier_id": selected.get("supplier_id"),
        "p50_days": p50,
        "p80_days": p80,
        "p90_days": p90,
        "minimum_feasible_days": minimum,
        "risk_level": risk,
        "warnings": warnings,
        "calculation_trace": traces,
    }


def _paths(payload: dict) -> dict:
    est = _estimate(payload)
    paths = []
    for i, t in enumerate(est["calculation_trace"], start=1):
        paths.append(
            {
                "path_id": f"single:{t['supplier_id']}",
                "rank": i,
                "mode": "SINGLE_SOURCE",
                "supplier_ids": [t["supplier_id"]],
                "estimated_lead_time_days": t["total_lead_time_days"],
                "earliest_delivery_date": est["earliest_delivery_date"],
                "feasible": t["feasible"],
                "confidence": t["confidence"],
                "score": 1.0,
                "warnings": [],
            }
        )
    return {"status": "ok", "supplier_count": est["supplier_count"], "paths": paths, "warnings": est["warnings"]}


def _reforecast(payload: dict) -> dict:
    est = _estimate(payload)
    return {
        "status": "ok",
        "baseline_lead_time_days": est["estimated_lead_time_days"],
        "updated_lead_time_days": est["estimated_lead_time_days"],
        "delta_days": 0,
        "earliest_delivery_date": est["earliest_delivery_date"],
        "feasible": est["feasible"],
        "supplier_count": est["supplier_count"],
        "selected_supplier_id": est["selected_supplier_id"],
        "applied_events": [],
        "warnings": est["warnings"],
        "calculation_trace": est["calculation_trace"],
    }


def route(method: str, path: str, body: dict | None) -> tuple[int, dict]:
    """Pure GLTG endpoint router (no HTTP library dependency)."""
    if path == "/health":
        return 200, {"status": "ok", "service": "gltg"}
    if path == "/version":
        return 200, {"service": "gltg", "version": "1.0.0", "api_version": "v1"}
    body = body or {}
    if path == "/v1/lead-time/estimate":
        return 200, _estimate(body)
    if path == "/v1/paths/enumerate":
        return 200, _paths(body)
    if path == "/v1/reforecast":
        return 200, _reforecast(body)
    return 404, {"detail": "not found"}


# --------------------------------------------------------------------------- #
# httpx MockTransport for unit tests
# --------------------------------------------------------------------------- #
def mock_transport():
    import httpx

    def handler(request: "httpx.Request") -> "httpx.Response":
        body = json.loads(request.content.decode() or "{}") if request.content else {}
        status, payload = route(request.method, request.url.path, body)
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)
