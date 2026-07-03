"""
Role Resolver — determines the contextual role of an actor in a project.

Core rule: an actor's role is determined by (project, edge, counterparty),
not by the actor's static type.

Same actor can be:
  - MAIN_M_SIDE when responding to the original buyer
  - UPSTREAM_B_SIDE when asking upstream suppliers
  - ORIGINAL_BUYER when initiating a project
"""
from __future__ import annotations
from src.actors.role_context import RoleContext
from src.m_side.m_event_logger import log_m_event


def resolve_role_context(
    project_id: str,
    actor_id: str,
    original_buyer_actor_id: str,
    main_supplier_actor_id: str | None = None,
    edge_id: str | None = None,
    edge_type: str | None = None,
    counterparty_actor_id: str | None = None,
) -> RoleContext:
    """
    Resolve the contextual role of actor_id within this project and edge.

    Resolution logic:
    1. Actor is original buyer → ORIGINAL_BUYER
    2. Actor is main supplier + edge is BUYER_TO_MAIN_SUPPLIER → MAIN_M_SIDE
    3. Actor is main supplier + edge is upstream type → UPSTREAM_B_SIDE
    4. Actor is NOT main supplier + edge is upstream type → UPSTREAM_M_SIDE
    5. Default → UNKNOWN
    """
    upstream_edge_types = {
        "MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        "MAIN_SUPPLIER_TO_TRIM_SUPPLIER",
        "MAIN_SUPPLIER_TO_MATERIAL_SUPPLIER",
        "MAIN_SUPPLIER_TO_COMPONENT_SUPPLIER",
        "MAIN_SUPPLIER_TO_SUBCONTRACTOR",
        "MAIN_SUPPLIER_TO_PACKAGING_SUPPLIER",
        "MAIN_SUPPLIER_TO_QC_PROVIDER",
        "MAIN_SUPPLIER_TO_LOGISTICS_PROVIDER",
    }

    # --- ORIGINAL_BUYER ---
    if actor_id == original_buyer_actor_id:
        rc = RoleContext(
            project_id=project_id,
            actor_id=actor_id,
            counterparty_actor_id=counterparty_actor_id or main_supplier_actor_id,
            edge_id=edge_id,
            role="ORIGINAL_BUYER",
            role_reason=(
                f"Actor {actor_id} is the original buyer who initiated project {project_id}."
            ),
            can_create_upstream_inquiry=False,
            can_approve_upstream_option=False,
            can_submit_response_to_buyer=False,
        )

    # --- MAIN_M_SIDE: main supplier receiving from original buyer ---
    elif (
        actor_id == main_supplier_actor_id
        and (edge_type is None or edge_type == "BUYER_TO_MAIN_SUPPLIER")
        and (counterparty_actor_id is None or counterparty_actor_id == original_buyer_actor_id)
    ):
        rc = RoleContext(
            project_id=project_id,
            actor_id=actor_id,
            counterparty_actor_id=counterparty_actor_id or original_buyer_actor_id,
            edge_id=edge_id,
            role="MAIN_M_SIDE",
            role_reason=(
                f"Actor {actor_id} is the main supplier for project {project_id}, "
                f"responding to original buyer {original_buyer_actor_id}."
            ),
            can_create_upstream_inquiry=True,
            can_approve_upstream_option=True,
            can_submit_response_to_buyer=True,
        )

    # --- UPSTREAM_B_SIDE: main supplier acting as buyer toward upstream ---
    elif actor_id == main_supplier_actor_id and edge_type in upstream_edge_types:
        rc = RoleContext(
            project_id=project_id,
            actor_id=actor_id,
            counterparty_actor_id=counterparty_actor_id,
            edge_id=edge_id,
            role="UPSTREAM_B_SIDE",
            role_reason=(
                f"Actor {actor_id} is acting as upstream buyer in project {project_id}, "
                f"sending inquiry to upstream supplier via edge {edge_id} ({edge_type})."
            ),
            can_create_upstream_inquiry=True,
            can_approve_upstream_option=True,
            can_submit_response_to_buyer=False,
        )

    # --- UPSTREAM_M_SIDE: upstream supplier responding to main supplier ---
    elif actor_id != main_supplier_actor_id and edge_type in upstream_edge_types:
        rc = RoleContext(
            project_id=project_id,
            actor_id=actor_id,
            counterparty_actor_id=counterparty_actor_id or main_supplier_actor_id,
            edge_id=edge_id,
            role="UPSTREAM_M_SIDE",
            role_reason=(
                f"Actor {actor_id} received an upstream inquiry from main supplier "
                f"{main_supplier_actor_id} in project {project_id}."
            ),
            can_create_upstream_inquiry=False,
            can_approve_upstream_option=False,
            can_submit_response_to_buyer=False,
        )

    else:
        rc = RoleContext(
            project_id=project_id,
            actor_id=actor_id,
            counterparty_actor_id=counterparty_actor_id,
            edge_id=edge_id,
            role="UNKNOWN",
            role_reason=f"Could not determine role for actor {actor_id} in project {project_id}.",
        )

    log_m_event(
        event_type="ROLE_CONTEXT_RESOLVED",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={
            "role": rc.role,
            "role_reason": rc.role_reason,
            "edge_id": edge_id,
            "edge_type": edge_type,
        },
    )
    return rc
