"""M-side upstream/subcontractor follow-up."""
from src.m_side.m_event_logger import log_m_event


def send_upstream_followup(
    project_id: str,
    supplier_actor_id: str,
    upstream_actor_id: str,
    dependency_type: str,
) -> dict:
    msg = f"Please confirm progress and the delivery time for {dependency_type.replace('_', ' ')}."
    log_m_event(
        event_type="M_UPSTREAM_FOLLOWUP_SENT",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"upstream_actor_id": upstream_actor_id, "dependency_type": dependency_type},
    )
    return {"status": "sent", "message": msg}
