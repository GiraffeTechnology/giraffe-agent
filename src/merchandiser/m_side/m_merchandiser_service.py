"""M-side AI Merchandiser — supplier-facing production coordination."""
from src.m_side.m_event_logger import log_m_event


def send_m_side_progress_check(project_id: str, supplier_actor_id: str, stage: str) -> dict:
    msg = (
        f"Progress check ({stage.replace('_', ' ')}): Please update the current production status."
    )
    log_m_event(
        event_type="M_SIDE_PROGRESS_CHECK_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"stage": stage, "message": msg},
    )
    return {"status": "sent", "message": msg}


def receive_m_side_progress_update(project_id: str, supplier_actor_id: str, update_text: str) -> dict:
    log_m_event(
        event_type="M_SIDE_PROGRESS_UPDATE_RECEIVED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"update": update_text[:200]},
    )
    return {"status": "received", "update": update_text}
