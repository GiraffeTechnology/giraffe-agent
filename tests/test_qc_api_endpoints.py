"""Tests for QC API endpoints."""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

_PROJECT = "PROJ-API-QC-01"

def test_add_reference_image_endpoint():
    resp = client.post(f"/api/qc/{_PROJECT}/reference-images", json={
        "image_path": "tests/fixtures/multimodal/red_square.png",
        "uploaded_by_actor_id": "ACT-BUYER-001",
        "milestone_type": "final_qc",
        "description": "Golden sample",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ref_image_id"].startswith("REF-")

def test_list_reference_images_endpoint():
    resp = client.get(f"/api/qc/{_PROJECT}/reference-images")
    assert resp.status_code == 200
    data = resp.json()
    assert "reference_images" in data

def test_create_process_card_endpoint():
    resp = client.post(f"/api/qc/{_PROJECT}/process-card", json={
        "category": "apparel",
        "color_spec": "Navy blue",
        "defect_criteria": "No pilling",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["process_card_id"].startswith("PC-")

def test_get_process_card_endpoint():
    # Create first
    client.post(f"/api/qc/PROJ-API-QC-GET-01/process-card", json={"category": "apparel"})
    resp = client.get("/api/qc/PROJ-API-QC-GET-01/process-card")
    assert resp.status_code == 200

def test_compare_qc_endpoint():
    resp = client.post(f"/api/qc/{_PROJECT}/compare", json={
        "production_images": [],
        "provider_name": "mock",
        "milestone_type": "final_qc",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_result" in data
    assert "provider_name" in data

def test_list_qc_reports_endpoint():
    resp = client.get(f"/api/qc/{_PROJECT}/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data

def test_buyer_qc_decision_endpoint():
    resp = client.post(f"/api/qc/{_PROJECT}/buyer-decision", json={
        "milestone_id": "MILE-001",
        "buyer_actor_id": "ACT-BUYER-001",
        "decision": "approve",
        "notes": "Looks good",
    })
    assert resp.status_code == 200

def test_qc_health_endpoint():
    resp = client.get("/api/qc/health")
    assert resp.status_code == 200
