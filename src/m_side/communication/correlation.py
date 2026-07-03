"""
Correlation token — links upstream supplier replies back to the correct project + dependency.
Format: GFR-{project_short}-DEP-{dep_type}-{supplier_short}
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from src.m_side.m_event_logger import log_m_event


@dataclass
class CorrelationResult:
    matched: bool
    project_id: str | None
    edge_id: str | None
    dependency_id: str | None
    raw_token: str | None
    confidence: float


def generate_correlation_token(
    project_id: str,
    edge_id: str,
    dependency_id: str,
) -> str:
    proj_short = project_id.replace("PROJ-", "")[:8]
    dep_short = dependency_id.replace("DEP-", "")[:8]
    edge_short = edge_id.replace("EDGE-", "")[:6]
    token = f"GFR-{proj_short}-DEP-{dep_short}-EDG-{edge_short}"
    log_m_event(
        event_type="MESSAGE_CORRELATION_TOKEN_CREATED",
        b_workspace_id=project_id,
        payload={"token": token, "edge_id": edge_id, "dependency_id": dependency_id},
    )
    return token


def resolve_correlation_token(raw_message: str, channel_context: dict) -> CorrelationResult:
    pattern = r"GFR-([A-Z0-9]+)-DEP-([A-Z0-9]+)-EDG-([A-Z0-9]+)"
    match = re.search(pattern, raw_message)
    if not match:
        return CorrelationResult(
            matched=False, project_id=None, edge_id=None,
            dependency_id=None, raw_token=None, confidence=0.0,
        )
    proj_short, dep_short, edge_short = match.group(1), match.group(2), match.group(3)
    token = match.group(0)

    project_id = channel_context.get("project_id") or f"PROJ-{proj_short}"
    edge_id = channel_context.get("edge_id") or f"EDGE-{edge_short}"
    dependency_id = f"DEP-{dep_short}"

    log_m_event(
        event_type="MESSAGE_CORRELATION_TOKEN_RESOLVED",
        b_workspace_id=project_id,
        payload={"token": token, "edge_id": edge_id, "dependency_id": dependency_id},
    )
    return CorrelationResult(
        matched=True,
        project_id=project_id,
        edge_id=edge_id,
        dependency_id=dependency_id,
        raw_token=token,
        confidence=0.95,
    )
