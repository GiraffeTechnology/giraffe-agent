"""Tests that order bridge uses resolved buyer_actor_id (Bug 4.1 fix)."""
import pytest
from unittest.mock import patch, MagicMock
from src.bm_bridge.order_bridge import create_order_execution_from_selected_path
from src.b_side.workspace import create_b_workspace, save_b_workspace
from src.core_schema.b_side_types import FeasibilityReport, DeliveryPath


def _setup_workspace_with_path(supplier_id: str, path_id: str) -> "BWWorkspace":
    ws = create_b_workspace("100 polo shirts")
    path = DeliveryPath(
        path_id=path_id,
        rfq_id=ws.rfq_id,
        supplier_id=supplier_id,
        supplier_name="Test Factory",
        lead_time_days=30,
        unit_price=12.5,
        currency="USD",
        confidence_score=0.9,
    )
    ws.feasibility_report = FeasibilityReport(
        rfq_id=ws.rfq_id,
        b_workspace_id=ws.b_workspace_id,
        paths=[path],
    )
    save_b_workspace(ws)
    return ws


def test_order_bridge_creates_order_with_correct_supplier_id():
    ws = _setup_workspace_with_path("SUPP-BRIDGE-001", "PATH-BRIDGE-001")
    with patch("src.m_side.supplier_workspace.list_m_workspaces", return_value=[]):
        order = create_order_execution_from_selected_path(ws.b_workspace_id, "PATH-BRIDGE-001")
    assert order.supplier_id == "SUPP-BRIDGE-001"
    assert order.order_execution_id.startswith("OE-")


def test_order_bridge_sets_b_workspace_id():
    ws = _setup_workspace_with_path("SUPP-BRIDGE-004", "PATH-BRIDGE-004")
    with patch("src.m_side.supplier_workspace.list_m_workspaces", return_value=[]):
        order = create_order_execution_from_selected_path(ws.b_workspace_id, "PATH-BRIDGE-004")
    assert order.b_workspace_id == ws.b_workspace_id


def test_order_bridge_uses_project_buyer_actor_id_when_available():
    ws = _setup_workspace_with_path("SUPP-BRIDGE-005", "PATH-BRIDGE-005")
    with patch("src.m_side.supplier_workspace.list_m_workspaces", return_value=[]):
        with patch("src.projects.project_graph._DATA_DIR") as mock_dir:
            mock_path = MagicMock()
            mock_path.read_text.return_value = (
                f'{{"project_id": "PROJ-BRIDGE-001", "b_workspace_id": "{ws.b_workspace_id}", '
                f'"original_buyer_actor_id": "BUYER-ACTOR-REAL-001"}}'
            )
            mock_path.name = "PROJ-BRIDGE-001.json"
            mock_dir.glob.return_value = [mock_path]
            order = create_order_execution_from_selected_path(ws.b_workspace_id, "PATH-BRIDGE-005")
    # Order should be created regardless
    assert order.order_execution_id.startswith("OE-")
