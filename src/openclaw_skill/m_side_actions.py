"""
M-side OpenClaw skill action handlers.
"""

from src.m_side.supplier_workspace import get_m_workspace
from src.m_side.response_collector import append_supplier_message, build_response_packet_from_messages
from src.m_side.supplier_clarification import next_supplier_question
from src.m_side.order_acknowledger import acknowledge_order
from src.m_side.production_update import submit_production_update
from src.m_side.qc_update import submit_qc_update
from src.m_side.logistics_update import submit_logistics_update
from src.m_side.exception_handler import submit_exception_report
from src.openclaw_skill.m_side_response_formatter import (
    format_m_workspace,
    format_response_packet_preview,
    format_order_execution,
)
from src.openclaw_skill.response_formatter import format_ok, format_error


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
    """Handler: m_side_submit_supplier_response — append message and build response packet."""
    m_workspace_id = params.get("m_workspace_id")
    message = params.get("message")
    if not m_workspace_id or not message:
        return format_error("m_workspace_id and message are required")

    try:
        # Append message
        workspace = append_supplier_message(m_workspace_id, message)

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

        return format_ok({
            "m_workspace_id": m_workspace_id,
            "status": workspace.status,
            "response_packet_preview": format_response_packet_preview(packet),
            "next_message": next_msg,
        })
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
