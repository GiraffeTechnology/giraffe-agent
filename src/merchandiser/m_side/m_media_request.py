"""M-side media upload request to suppliers."""
from src.m_side.m_event_logger import log_m_event


def request_milestone_media_upload(
    project_id: str,
    supplier_actor_id: str,
    milestone_id: str,
    milestone_type: str,
    required_media: list[str],
) -> dict:
    media_desc = ", ".join(required_media) if required_media else "photos"
    msg = (
        f"Please upload {milestone_type.replace('_', ' ')} stage media: {media_desc}."
    )
    log_m_event(
        event_type="ORDER_MILESTONE_MEDIA_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"milestone_id": milestone_id, "milestone_type": milestone_type, "message": msg},
    )
    return {"status": "requested", "message": msg}
