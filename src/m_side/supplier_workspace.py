"""
M-side supplier workspace persistence — JSON file storage under data/m_side_workspaces/.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.core_schema.m_side_types import MSideWorkspace, SupplierInquiryContext, MSideSupplierProfile

_DATA_DIR = Path("data/m_side_workspaces")
_TOKEN_INDEX = Path("data/m_side_workspaces/_token_index.json")


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _workspace_path(m_workspace_id: str) -> Path:
    return _DATA_DIR / f"{m_workspace_id}.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_token_index() -> dict:
    _ensure_dir()
    if _TOKEN_INDEX.exists():
        with open(_TOKEN_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_token_index(index: dict) -> None:
    _ensure_dir()
    with open(_TOKEN_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def create_m_workspace(
    inquiry_context: SupplierInquiryContext,
    supplier_profile: MSideSupplierProfile,
) -> MSideWorkspace:
    """Create and persist a supplier-side workspace linked to a B-side workspace."""
    _ensure_dir()
    now = _utcnow()
    workspace = MSideWorkspace(
        m_workspace_id=inquiry_context.m_workspace_id,
        b_workspace_id=inquiry_context.b_workspace_id,
        rfq_id=inquiry_context.rfq_id,
        inquiry_id=inquiry_context.inquiry_id,
        supplier_id=inquiry_context.supplier_id,
        supplier_name=inquiry_context.supplier_name,
        status="inquiry_received",
        created_at=now,
        updated_at=now,
        channel_id=supplier_profile.channel,
        external_user_id=supplier_profile.external_user_id,
        invitation_token=inquiry_context.invitation_token,
        inquiry_context=inquiry_context,
    )
    return save_m_workspace(workspace)


def get_m_workspace(m_workspace_id: str) -> MSideWorkspace:
    """Load a persisted M-side workspace by ID."""
    _ensure_dir()
    path = _workspace_path(m_workspace_id)
    if not path.exists():
        raise FileNotFoundError(f"M-side workspace not found: {m_workspace_id}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MSideWorkspace.model_validate(data)


def save_m_workspace(workspace: MSideWorkspace) -> MSideWorkspace:
    """Persist M-side workspace and update updated_at."""
    _ensure_dir()
    workspace.updated_at = _utcnow()
    path = _workspace_path(workspace.m_workspace_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workspace.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    # Update token index
    if workspace.invitation_token:
        index = _load_token_index()
        index[workspace.invitation_token] = workspace.m_workspace_id
        _save_token_index(index)

    return workspace


def update_m_workspace_status(m_workspace_id: str, status: str) -> MSideWorkspace:
    """Update supplier workspace status and persist."""
    workspace = get_m_workspace(m_workspace_id)
    workspace.status = status
    return save_m_workspace(workspace)


def find_workspace_by_invitation_token(token: str) -> MSideWorkspace | None:
    """Resolve supplier workspace from an invitation token."""
    index = _load_token_index()
    m_workspace_id = index.get(token)
    if m_workspace_id is None:
        return None
    try:
        return get_m_workspace(m_workspace_id)
    except FileNotFoundError:
        return None


def find_active_workspace_for_supplier(channel: str, external_user_id: str) -> MSideWorkspace | None:
    """Resolve active supplier workspace from IM identity (channel + user ID)."""
    _ensure_dir()
    for path in sorted(_DATA_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ws = MSideWorkspace.model_validate(data)
            if (
                ws.channel_id == channel
                and ws.external_user_id == external_user_id
                and ws.status not in ("completed", "closed", "exception_reported")
            ):
                return ws
        except Exception:
            pass
    return None


def list_m_workspaces() -> list[MSideWorkspace]:
    """List all persisted M-side workspaces."""
    _ensure_dir()
    workspaces = []
    for path in sorted(_DATA_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            workspaces.append(MSideWorkspace.model_validate(data))
        except Exception:
            pass
    return workspaces


def find_workspace_by_rfq_id(rfq_id: str) -> MSideWorkspace | None:
    """
    Resolve an active M-side workspace by RFQ id.

    OpenClaw supplier replies may pass the B-side RFQ id as project_id.
    Persisted MSideWorkspace stores this value in workspace.rfq_id — not
    in b_rfq_id or project_id, which do not exist on the model.

    Returns:
        MSideWorkspace if exactly one active workspace matches.
        None if no workspace matches.

    Raises:
        ValueError: if multiple active workspaces share the same rfq_id,
                    to prevent silently selecting the wrong workspace.
    """
    _ensure_dir()
    matches: list[MSideWorkspace] = []
    for path in sorted(_DATA_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ws = MSideWorkspace.model_validate(data)
            if ws.rfq_id == rfq_id and ws.status not in ("completed", "closed", "exception_reported"):
                matches.append(ws)
        except Exception:
            pass
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    raise ValueError(
        f"ambiguous_m_workspace: {len(matches)} active M-side workspaces share rfq_id={rfq_id!r}"
    )


def find_active_workspace_for_supplier_and_rfq(
    channel: str | None,
    external_user_id: str | None,
    rfq_id: str,
) -> MSideWorkspace | None:
    """
    Resolve active M-side workspace by RFQ id plus supplier channel identity.

    Matching priority:
    1. rfq_id + channel + external_user_id (most specific — returns on first hit)
    2. rfq_id alone as fallback if unambiguous (delegates to find_workspace_by_rfq_id)

    Raises ValueError if fallback to rfq_id-only lookup finds multiple workspaces.
    """
    _ensure_dir()
    if channel and external_user_id:
        for path in sorted(_DATA_DIR.glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ws = MSideWorkspace.model_validate(data)
                if (
                    ws.rfq_id == rfq_id
                    and ws.channel_id == channel
                    and ws.external_user_id == external_user_id
                    and ws.status not in ("completed", "closed", "exception_reported")
                ):
                    return ws
            except Exception:
                pass
    return find_workspace_by_rfq_id(rfq_id)
