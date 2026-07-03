"""
Message router — determines direction, business role, and parser target for incoming messages.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from src.m_side.m_event_logger import log_m_event


@dataclass
class RoutedMessageContext:
    project_id: str
    edge_id: str | None
    actor_id: str
    counterparty_actor_id: str | None
    thread_id: str | None
    role_context_id: str
    business_role: str
    communication_direction: Literal["INBOUND", "OUTBOUND", "INTERNAL"]
    message_purpose: str
    parser_target: Literal[
        "buyer_requirement_parser",
        "buyer_confirmation_parser",
        "upstream_response_parser",
        "approval_parser",
        "progress_update_parser",
        "media_parser",
        "logistics_parser",
        "buyer_signoff_parser",
        "exception_parser",
        "unknown",
    ]
    confidence_score: float


def route_incoming_message(raw_message: str, channel_context: dict) -> RoutedMessageContext:
    """
    Route an incoming message based on the channel context (thread_type, from_actor, etc.).
    """
    project_id = channel_context.get("project_id", "unknown")
    thread_type = channel_context.get("thread_type", "")
    actor_id = channel_context.get("actor_id", "unknown")
    counterparty_id = channel_context.get("counterparty_actor_id")
    thread_id = channel_context.get("thread_id")
    role_context_id = channel_context.get("role_context_id", "rc-unknown")

    msg_lower = raw_message.lower()

    if thread_type in ("buyer_main_supplier", "buyer_rollup_review"):
        if any(kw in msg_lower for kw in ("confirm", "confirmed", "ok", "proceed", "accepted")):
            return RoutedMessageContext(
                project_id=project_id, edge_id=channel_context.get("edge_id"),
                actor_id=actor_id, counterparty_actor_id=counterparty_id,
                thread_id=thread_id, role_context_id=role_context_id,
                business_role="MAIN_M_SIDE", communication_direction="INBOUND",
                message_purpose="buyer_rollup_confirmation",
                parser_target="buyer_confirmation_parser", confidence_score=0.88,
            )
        return RoutedMessageContext(
            project_id=project_id, edge_id=channel_context.get("edge_id"),
            actor_id=actor_id, counterparty_actor_id=counterparty_id,
            thread_id=thread_id, role_context_id=role_context_id,
            business_role="MAIN_M_SIDE", communication_direction="INBOUND",
            message_purpose="buyer_inquiry_received",
            parser_target="buyer_requirement_parser", confidence_score=0.85,
        )

    if thread_type == "main_supplier_upstream":
        return RoutedMessageContext(
            project_id=project_id, edge_id=channel_context.get("edge_id"),
            actor_id=actor_id, counterparty_actor_id=counterparty_id,
            thread_id=thread_id, role_context_id=role_context_id,
            business_role="UPSTREAM_B_SIDE", communication_direction="INBOUND",
            message_purpose="upstream_response_received",
            parser_target="upstream_response_parser", confidence_score=0.9,
        )

    if thread_type == "main_supplier_internal_approval":
        return RoutedMessageContext(
            project_id=project_id, edge_id=channel_context.get("edge_id"),
            actor_id=actor_id, counterparty_actor_id=counterparty_id,
            thread_id=thread_id, role_context_id=role_context_id,
            business_role="MAIN_M_SIDE", communication_direction="INTERNAL",
            message_purpose="upstream_option_approval_request",
            parser_target="approval_parser", confidence_score=0.92,
        )

    if thread_type == "logistics_handover":
        return RoutedMessageContext(
            project_id=project_id, edge_id=channel_context.get("edge_id"),
            actor_id=actor_id, counterparty_actor_id=counterparty_id,
            thread_id=thread_id, role_context_id=role_context_id,
            business_role="MAIN_M_SIDE", communication_direction="INBOUND",
            message_purpose="logistics_handover",
            parser_target="logistics_parser", confidence_score=0.9,
        )

    if thread_type == "buyer_signoff":
        return RoutedMessageContext(
            project_id=project_id, edge_id=channel_context.get("edge_id"),
            actor_id=actor_id, counterparty_actor_id=counterparty_id,
            thread_id=thread_id, role_context_id=role_context_id,
            business_role="ORIGINAL_BUYER", communication_direction="INBOUND",
            message_purpose="buyer_signoff_response",
            parser_target="buyer_signoff_parser", confidence_score=0.88,
        )

    # Low confidence fallback
    log_m_event(
        event_type="MESSAGE_ROUTING_LOW_CONFIDENCE",
        b_workspace_id=project_id,
        payload={"thread_type": thread_type, "message_preview": raw_message[:80]},
    )
    return RoutedMessageContext(
        project_id=project_id, edge_id=channel_context.get("edge_id"),
        actor_id=actor_id, counterparty_actor_id=counterparty_id,
        thread_id=thread_id, role_context_id=role_context_id,
        business_role="UNKNOWN", communication_direction="INBOUND",
        message_purpose="unknown", parser_target="unknown", confidence_score=0.3,
    )
