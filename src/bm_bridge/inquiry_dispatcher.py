"""
B+M Bridge — Inquiry Dispatcher.
Dispatches B-side supplier inquiry to selected suppliers, creating M-side workspaces.
"""

import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import SupplierInquiryContext
from src.b_side.workspace import get_b_workspace
from src.m_side.supplier_profile import get_supplier_profile, create_supplier_profile
from src.m_side.supplier_workspace import create_m_workspace
from src.m_side.supplier_identity import create_invitation_token
from src.m_side.inquiry_receiver import receive_supplier_inquiry, format_inquiry_for_supplier
from src.m_side.m_event_logger import log_m_event
from src.channels.router import _get_adapter as get_adapter
from src.channels.base import OutboundChannelMessage
from src.bm_bridge.notifications import notify_supplier_inquiry_dispatched


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def dispatch_supplier_inquiry(
    b_workspace_id: str,
    supplier_ids: list[str],
    channel: str = "mock",
) -> list[SupplierInquiryContext]:
    """
    Create M-side workspaces and dispatch the B-side supplier inquiry to selected suppliers.

    Steps per supplier:
    1. Load B-side workspace and get inquiry draft
    2. Create invitation token
    3. Build SupplierInquiryContext
    4. Create MSideWorkspace
    5. Send dispatch message through channel adapter
    6. Log M_SUPPLIER_INQUIRY_DISPATCHED event
    """
    workspace = get_b_workspace(b_workspace_id)
    draft = workspace.supplier_inquiry_draft

    if draft is None:
        raise ValueError(f"No supplier inquiry draft in workspace {b_workspace_id}")

    req = workspace.buyer_requirement
    rfq_id = req.rfq_id if req else workspace.rfq_id

    adapter = get_adapter(channel)
    contexts: list[SupplierInquiryContext] = []

    for supplier_id in supplier_ids:
        # Load or create supplier profile
        profile = get_supplier_profile(supplier_id)
        if profile is None:
            profile = create_supplier_profile(
                supplier_id=supplier_id,
                name=f"Supplier {supplier_id}",
                channel=channel,
            )

        # Create invitation token
        token = create_invitation_token(
            b_workspace_id=b_workspace_id,
            inquiry_id=draft.inquiry_id,
            supplier_id=supplier_id,
        )

        # Create M-side workspace ID
        m_workspace_id = f"mw_{uuid.uuid4().hex[:12]}"

        # Build inquiry context
        context = SupplierInquiryContext(
            m_workspace_id=m_workspace_id,
            b_workspace_id=b_workspace_id,
            rfq_id=rfq_id,
            inquiry_id=draft.inquiry_id,
            supplier_id=supplier_id,
            supplier_name=profile.supplier_name,
            invitation_token=token,
            inquiry_text_zh=draft.message_text_zh,
            inquiry_text_en=draft.message_text_en,
            required_response_fields=draft.required_fields,
            created_at=_utcnow(),
        )

        # Create M-side workspace
        m_workspace = receive_supplier_inquiry(context)

        # Send dispatch message through channel
        dispatch_msg = format_inquiry_for_supplier(
            context,
            language=profile.language_preference or "zh",
        )
        to_user = profile.external_user_id or supplier_id
        outbound = OutboundChannelMessage(
            channel=channel,
            to_external_user_id=to_user,
            text=dispatch_msg,
        )
        adapter.send_message(outbound)

        # Log event
        log_m_event(
            event_type="M_SUPPLIER_INQUIRY_DISPATCHED",
            m_workspace_id=m_workspace_id,
            b_workspace_id=b_workspace_id,
            supplier_id=supplier_id,
            rfq_id=rfq_id,
            payload={
                "inquiry_id": draft.inquiry_id,
                "invitation_token": token,
                "channel": channel,
            },
        )

        # Stub notification
        notify_supplier_inquiry_dispatched(
            supplier_id=supplier_id,
            m_workspace_id=m_workspace_id,
            token=token,
        )

        contexts.append(context)

    return contexts
