"""
M-side OpenClaw skill action handlers.
"""

from src.m_side.supplier_workspace import (
    get_m_workspace,
    find_workspace_by_rfq_id,
    find_active_workspace_for_supplier_and_rfq,
)
from src.m_side.response_collector import append_supplier_message, build_response_packet_from_messages
from src.m_side.supplier_clarification import next_supplier_question
from src.m_side.order_acknowledger import acknowledge_order
from src.m_side.production_update import submit_production_update
from src.m_side.qc_update import submit_qc_update
from src.m_side.logistics_update import submit_logistics_update
from src.m_side.exception_handler import submit_exception_report
from src.m_side.m_event_logger import log_m_event
from src.openclaw_skill.m_side_response_formatter import (
    format_m_workspace,
    format_response_packet_preview,
    format_order_execution,
)
from src.openclaw_skill.response_formatter import format_ok, format_error


def _resolve_m_workspace(params: dict):
    """
    Resolve M-side workspace from action params.

    Lookup priority:
    1. Explicit m_workspace_id — use directly.
    2. rfq_id + channel identity (sender_id / channel) — most specific RFQ lookup.
    3. project_id treated as rfq_id — fallback when only project_id is provided.

    Returns (workspace, None) on success.
    Returns (None, error_dict) on failure (not found, ambiguous, or missing required params).
    """
    m_workspace_id = params.get("m_workspace_id")

    # Priority 1: explicit workspace id
    if m_workspace_id:
        try:
            ws = get_m_workspace(m_workspace_id)
            return ws, None
        except FileNotFoundError:
            return None, {
                "ok": False,
                "status": "m_workspace_not_found",
                "reply_text": (
                    f"未找到 workspace {m_workspace_id}。请确认工作区编号。"
                ),
                "missing_fields": [],
                "message_drafts": [],
                "outbound_messages": [],
            }

    # Priority 2 & 3: resolve by rfq_id (project_id is the RFQ id returned by B-side)
    rfq_id = params.get("rfq_id") or params.get("project_id")
    if not rfq_id:
        return None, {
            "ok": False,
            "status": "m_workspace_not_found",
            "reply_text": (
                "未找到与该 RFQ / 项目对应的供应商工作区。请确认项目编号或供应商身份。"
            ),
            "missing_fields": ["m_workspace_id_or_supplier_binding"],
            "message_drafts": [],
            "outbound_messages": [],
        }

    channel = params.get("channel")
    sender_id = params.get("sender_id") or params.get("external_user_id")

    try:
        ws = find_active_workspace_for_supplier_and_rfq(channel, sender_id, rfq_id)
    except ValueError:
        # Multiple workspaces share the same rfq_id — cannot pick one safely
        return None, {
            "ok": False,
            "status": "ambiguous_m_workspace",
            "reply_text": (
                "找到多个可能的供应商工作区。请指定供应商或 inquiry/workspace id。"
            ),
            "message_drafts": [],
            "outbound_messages": [],
        }

    if ws is None:
        return None, {
            "ok": False,
            "status": "m_workspace_not_found",
            "reply_text": (
                "未找到与该 RFQ / 项目对应的供应商工作区。请确认项目编号或供应商身份。"
            ),
            "missing_fields": ["m_workspace_id_or_supplier_binding"],
            "message_drafts": [],
            "outbound_messages": [],
        }

    return ws, None


def handle_m_side_receive_inquiry(params: dict) -> dict:
    """Handler: m_side_receive_inquiry — load and return M-side workspace."""
    m_workspace_id = params.get("m_workspace_id")
    if not m_workspace_id:
        return format_error("m_workspace_id is required")
    try:
        workspace = get_m_workspace(m_workspace_id)
        return format_ok({"workspace": format_m_workspace(workspace)})
    except FileNotFoundError:
        return format_error(f"Workspace {m_workspace_id} not found")


def handle_m_side_submit_supplier_response(params: dict) -> dict:
    """
    Handler: m_side_submit_supplier_response — append supplier message and build response packet.

    Accepts workspace identification via:
    - m_workspace_id (explicit, highest priority)
    - project_id (treated as rfq_id from the B-side flow) + optional sender_id/channel
    - rfq_id + optional sender_id/channel

    Returns status="supplier_response_received" only after the message is actually appended.
    Returns status="m_workspace_not_found" or "ambiguous_m_workspace" if lookup fails.
    """
    # Accept both "message" and "message_text" (OpenClaw event field name)
    message = params.get("message") or params.get("message_text")
    if not message:
        return format_error("message or message_text is required")

    workspace, error = _resolve_m_workspace(params)
    if error is not None:
        return error

    m_workspace_id = workspace.m_workspace_id
    attachments = params.get("attachments", [])

    try:
        # Append message — this is the critical action; must succeed before returning success
        workspace = append_supplier_message(m_workspace_id, message, attachments)

        # Build response packet
        packet = build_response_packet_from_messages(m_workspace_id)
        workspace = get_m_workspace(m_workspace_id)

        # Get next question if incomplete
        next_q = next_supplier_question(workspace)
        next_msg = (
            next_q
            if next_q
            else '已整理为结构化供应商响应。请确认是否提交给买方：回复"确认提交"。'
        )

        log_m_event(
            event_type="M_SUPPLIER_RESPONSE_HANDLER_COMPLETED",
            m_workspace_id=m_workspace_id,
            b_workspace_id=workspace.b_workspace_id,
            supplier_id=workspace.supplier_id,
            rfq_id=workspace.rfq_id,
            payload={"message_count": len(workspace.raw_supplier_messages)},
        )

        return {
            "ok": True,
            "status": "supplier_response_received",
            "m_workspace_id": m_workspace_id,
            "workspace_status": workspace.status,
            "response_packet_preview": format_response_packet_preview(packet),
            "next_message": next_msg,
        }
    except Exception as e:
        return format_error(str(e))


def handle_m_side_get_pending_question(params: dict) -> dict:
    """Handler: m_side_get_pending_question — get next missing field question."""
    m_workspace_id = params.get("m_workspace_id")
    if not m_workspace_id:
        return format_error("m_workspace_id is required")
    try:
        workspace = get_m_workspace(m_workspace_id)
        question = next_supplier_question(workspace)
        return format_ok({
            "m_workspace_id": m_workspace_id,
            "next_question": question,
            "has_pending_questions": question is not None,
        })
    except FileNotFoundError:
        return format_error(f"Workspace {m_workspace_id} not found")


def handle_m_side_submit_order_acknowledgement(params: dict) -> dict:
    """Handler: m_side_submit_order_acknowledgement."""
    order_execution_id = params.get("order_execution_id")
    message = params.get("message", "确认接单")
    if not order_execution_id:
        return format_error("order_execution_id is required")
    try:
        order = acknowledge_order(order_execution_id, message)
        return format_ok({
            "order_execution_id": order_execution_id,
            "status": order.status,
            "order": format_order_execution(order),
        })
    except FileNotFoundError:
        return format_error(f"Order {order_execution_id} not found")


def handle_m_side_submit_production_update(params: dict) -> dict:
    """Handler: m_side_submit_production_update."""
    order_execution_id = params.get("order_execution_id")
    supplier_id = params.get("supplier_id")
    message = params.get("message")
    attachments = params.get("attachments", [])
    if not order_execution_id or not supplier_id or not message:
        return format_error("order_execution_id, supplier_id, and message are required")
    update = submit_production_update(order_execution_id, supplier_id, message, attachments)
    return format_ok({"update_id": update.update_id, "status": update.status})


def handle_m_side_submit_qc_update(params: dict) -> dict:
    """Handler: m_side_submit_qc_update."""
    order_execution_id = params.get("order_execution_id")
    supplier_id = params.get("supplier_id")
    message = params.get("message")
    attachments = params.get("attachments", [])
    if not order_execution_id or not supplier_id or not message:
        return format_error("order_execution_id, supplier_id, and message are required")
    qc = submit_qc_update(order_execution_id, supplier_id, message, attachments)
    return format_ok({"qc_update_id": qc.qc_update_id, "qc_status": qc.qc_status})


def handle_m_side_submit_logistics_update(params: dict) -> dict:
    """Handler: m_side_submit_logistics_update."""
    order_execution_id = params.get("order_execution_id")
    supplier_id = params.get("supplier_id")
    message = params.get("message")
    if not order_execution_id or not supplier_id or not message:
        return format_error("order_execution_id, supplier_id, and message are required")
    lgs = submit_logistics_update(order_execution_id, supplier_id, message)
    return format_ok({
        "logistics_update_id": lgs.logistics_update_id,
        "status": lgs.status,
        "tracking_number": lgs.tracking_number,
        "carrier": lgs.carrier,
    })


def handle_m_side_report_exception(params: dict) -> dict:
    """Handler: m_side_report_exception."""
    m_workspace_id = params.get("m_workspace_id")
    supplier_id = params.get("supplier_id")
    message = params.get("message")
    order_execution_id = params.get("order_execution_id")
    if not m_workspace_id or not supplier_id or not message:
        return format_error("m_workspace_id, supplier_id, and message are required")
    exc = submit_exception_report(m_workspace_id, supplier_id, message, order_execution_id)
    return format_ok({
        "exception_id": exc.exception_id,
        "severity": exc.severity,
        "category": exc.category,
    })
