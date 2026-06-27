"""Feasibility/lead-time now flows through the standalone GLTG API client.

These replace the deleted embedded-engine tests. They assert the integration
contract (giraffe-agent calls GLTG and maps the response) rather than any local
calculation -- the calculation itself is owned and tested by the GLTG repo.
"""

from __future__ import annotations

import httpx
import pytest

from src.integrations.gltg_leadtime import GLTGUnavailableError, estimate_lead_time_path


def _path(**over):
    kwargs = dict(
        supplier_response_id="R1",
        supplier_id="S1",
        supplier_name="Supplier 1",
        project_id="P1",
        quantity=10000,
        fabric_days=5,
        qc_days=2,
        logistics_days=7,
        subcontract_days=14,
        confidence_score=0.8,
        buyer_deadline_days=120,
    )
    kwargs.update(over)
    return estimate_lead_time_path(**kwargs)


def test_lead_time_path_populated_from_gltg_api():
    p = _path()
    assert p.total_lead_time_days > 0
    assert p.p50_lead_time_days is not None
    assert p.p80_lead_time_days >= p.p50_lead_time_days
    assert p.p90_lead_time_days >= p.p80_lead_time_days
    assert p.model_name == "GLTG"
    assert p.fallback_model_used is False
    # components carry the GLTG stage breakdown
    types = {c.component_type for c in p.components}
    assert {"material", "production", "qc", "logistics"} <= types


def test_deadline_feasibility_reflects_gltg_response():
    feasible = _path(buyer_deadline_days=400)
    assert feasible.feasible_before_deadline is True
    tight = _path(buyer_deadline_days=5)
    assert tight.feasible_before_deadline is False


def test_no_silent_fallback_on_gltg_failure():
    from src.integrations.gltg_client import GLTGClient

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = GLTGClient(base_url="http://gltg.test", transport=httpx.MockTransport(boom))
    with pytest.raises(GLTGUnavailableError):
        _path(client=client)
