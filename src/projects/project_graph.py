"""
Project graph persistence — JSON file storage for ProcurementProject and ProcurementEdge.
Data stored under data/projects/.
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.projects.models import ProcurementEdge, ProcurementProject

_DATA_DIR = Path("data/projects")


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _project_path(project_id: str) -> Path:
    return _DATA_DIR / f"{project_id}.json"


def _edges_path(project_id: str) -> Path:
    return _DATA_DIR / f"{project_id}_edges.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(
    original_buyer_actor_id: str,
    product_summary: str,
    category: str,
    quantity: int | None = None,
    main_supplier_actor_id: str | None = None,
    b_workspace_id: str | None = None,
    metadata: dict | None = None,
) -> ProcurementProject:
    _ensure_dir()
    project = ProcurementProject(
        project_id=f"PROJ-{uuid.uuid4().hex[:10].upper()}",
        original_buyer_actor_id=original_buyer_actor_id,
        main_supplier_actor_id=main_supplier_actor_id,
        b_workspace_id=b_workspace_id,
        product_summary=product_summary,
        category=category,
        quantity=quantity,
        metadata=metadata or {},
    )
    return save_project(project)


def get_project(project_id: str) -> ProcurementProject:
    _ensure_dir()
    path = _project_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"Project not found: {project_id}")
    with open(path, "r", encoding="utf-8") as f:
        return ProcurementProject.model_validate(json.load(f))


def save_project(project: ProcurementProject) -> ProcurementProject:
    _ensure_dir()
    project.updated_at = _utcnow()
    path = _project_path(project.project_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return project


def update_project_status(project_id: str, status: str) -> ProcurementProject:
    project = get_project(project_id)
    project.status = status  # type: ignore[assignment]
    return save_project(project)


def set_main_supplier(project_id: str, main_supplier_actor_id: str) -> ProcurementProject:
    project = get_project(project_id)
    project.main_supplier_actor_id = main_supplier_actor_id
    return save_project(project)


# ── Edges ─────────────────────────────────────────────────────────────────────

def _load_edges(project_id: str) -> list[ProcurementEdge]:
    path = _edges_path(project_id)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [ProcurementEdge.model_validate(e) for e in data]


def _save_edges(project_id: str, edges: list[ProcurementEdge]) -> None:
    _ensure_dir()
    path = _edges_path(project_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([e.model_dump(mode="json") for e in edges], f, ensure_ascii=False, indent=2)


def create_edge(
    project_id: str,
    from_actor_id: str,
    to_actor_id: str,
    edge_type: str,
    parent_edge_id: str | None = None,
    inquiry_id: str | None = None,
) -> ProcurementEdge:
    _ensure_dir()
    edge = ProcurementEdge(
        edge_id=f"EDGE-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        from_actor_id=from_actor_id,
        to_actor_id=to_actor_id,
        edge_type=edge_type,  # type: ignore[arg-type]
        parent_edge_id=parent_edge_id,
        inquiry_id=inquiry_id,
    )
    edges = _load_edges(project_id)
    edges.append(edge)
    _save_edges(project_id, edges)
    return edge


def get_edge(project_id: str, edge_id: str) -> ProcurementEdge:
    for edge in _load_edges(project_id):
        if edge.edge_id == edge_id:
            return edge
    raise FileNotFoundError(f"Edge {edge_id} not found in project {project_id}")


def get_edges_for_project(project_id: str) -> list[ProcurementEdge]:
    return _load_edges(project_id)


def update_edge_status(project_id: str, edge_id: str, status: str) -> ProcurementEdge:
    edges = _load_edges(project_id)
    updated = None
    for e in edges:
        if e.edge_id == edge_id:
            e.status = status  # type: ignore[assignment]
            e.updated_at = _utcnow()
            updated = e
            break
    if updated is None:
        raise FileNotFoundError(f"Edge {edge_id} not found")
    _save_edges(project_id, edges)
    return updated


def attach_inquiry_to_edge(project_id: str, edge_id: str, inquiry_id: str) -> ProcurementEdge:
    edges = _load_edges(project_id)
    updated = None
    for e in edges:
        if e.edge_id == edge_id:
            e.inquiry_id = inquiry_id
            e.updated_at = _utcnow()
            updated = e
            break
    if updated is None:
        raise FileNotFoundError(f"Edge {edge_id} not found")
    _save_edges(project_id, edges)
    return updated


def attach_response_to_edge(project_id: str, edge_id: str, response_id: str) -> ProcurementEdge:
    edges = _load_edges(project_id)
    updated = None
    for e in edges:
        if e.edge_id == edge_id:
            e.response_id = response_id
            e.updated_at = _utcnow()
            updated = e
            break
    if updated is None:
        raise FileNotFoundError(f"Edge {edge_id} not found")
    _save_edges(project_id, edges)
    return updated
