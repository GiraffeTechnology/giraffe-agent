"""
Giraffe Agent FastAPI application — B-side + M-side endpoints + OpenClaw skill invocation.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Giraffe Agent MVP API",
    description="B-side AI Buyer + M-side AI Merchandiser / Supplier Response Agent",
    version="0.1.0",
)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "giraffe-agent"}


# ─── OpenClaw Skill Invocation ─────────────────────────────────────────────────

class SkillInvokeRequest(BaseModel):
    # Legacy action-based invocation
    action: str | None = None
    channel: str | None = None
    external_user_id: str | None = None
    params: dict = {}

    # OpenClaw normalized channel event fields
    source: str | None = None
    channel_account_id: str | None = None
    conversation_id: str | None = None
    sender_id: str | None = None
    sender_display_name: str | None = None
    message_text: str | None = None
    message_type: str | None = None
    attachments: list = []
    timestamp: str | None = None
    project_id: str | None = None
    procurement_edge_id: str | None = None
    actor_id: str | None = None
    role_context: str | None = None
    mode: str | None = None


@app.post("/api/skill/invoke")
def invoke_skill(request: SkillInvokeRequest):
    """
    OpenClaw skill invocation endpoint.

    Supports two formats:
    1. Legacy action-based: { "action": "m_side_receive_inquiry", "params": {...} }
    2. OpenClaw normalized event: { "source": "openclaw", "channel": "openclaw-weixin", ... }
    """
    # Detect OpenClaw normalized event format
    if request.source == "openclaw" or (
        request.action is None and request.conversation_id is not None
    ):
        from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
        event_data = {
            "source": request.source or "openclaw",
            "channel": request.channel or "openclaw-unknown",
            "channel_account_id": request.channel_account_id or "",
            "conversation_id": request.conversation_id or "",
            "sender_id": request.sender_id or "",
            "sender_display_name": request.sender_display_name,
            "message_text": request.message_text or "",
            "message_type": request.message_type or "text",
            "attachments": request.attachments or [],
            "timestamp": request.timestamp,
            "project_id": request.project_id,
            "procurement_edge_id": request.procurement_edge_id,
            "actor_id": request.actor_id,
            "role_context": request.role_context,
            "mode": request.mode,
        }
        return adapt_openclaw_event(event_data)

    # Legacy action-based invocation
    if not request.action:
        return {"ok": False, "error": "Either 'action' or OpenClaw event fields are required"}

    from src.openclaw_skill.skill_router import route_action
    params = dict(request.params)
    if request.external_user_id:
        params.setdefault("external_user_id", request.external_user_id)
    if request.channel:
        params.setdefault("channel", request.channel)
    return route_action(request.action, params)


# ─── B-side workspace endpoints ────────────────────────────────────────────────

class CreateWorkspaceRequest(BaseModel):
    raw_requirement: str


@app.post("/api/b-side/workspaces")
def create_b_workspace(request: CreateWorkspaceRequest):
    from src.b_side.workspace import create_b_workspace as _create
    workspace = _create(request.raw_requirement)
    return workspace.model_dump(mode="json")


@app.get("/api/b-side/workspaces/{b_workspace_id}")
def get_b_workspace(b_workspace_id: str):
    from src.b_side.workspace import get_b_workspace as _get
    try:
        workspace = _get(b_workspace_id)
        return workspace.model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace {b_workspace_id} not found")


@app.post("/api/b-side/workspaces/{b_workspace_id}/structure-requirement")
def structure_requirement(b_workspace_id: str):
    from src.b_side.workspace import get_b_workspace as _get, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement as _struct
    try:
        workspace = _get(b_workspace_id)
        req = _struct(b_workspace_id, workspace.raw_requirement)
        workspace.buyer_requirement = req
        workspace.status = "requirement_structured"
        save_b_workspace(workspace)
        return req.model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace {b_workspace_id} not found")


class DraftInquiryRequest(BaseModel):
    supplier_ids: list[str]


@app.post("/api/b-side/workspaces/{b_workspace_id}/draft-inquiry")
def draft_inquiry(b_workspace_id: str, request: DraftInquiryRequest):
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.b_side.workspace import get_b_workspace as _get, save_b_workspace
    try:
        draft = draft_supplier_inquiry(b_workspace_id, request.supplier_ids)
        workspace = _get(b_workspace_id)
        workspace.supplier_inquiry_draft = draft
        workspace.status = "inquiry_drafted"
        save_b_workspace(workspace)
        return draft.model_dump(mode="json")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/b-side/workspaces/{b_workspace_id}/run-feasibility")
def run_feasibility(b_workspace_id: str):
    from src.b_side.feasibility_engine import run_feasibility_simulation
    try:
        report = run_feasibility_simulation(b_workspace_id)
        return report.model_dump(mode="json")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── M-side supplier profile endpoints ────────────────────────────────────────

class CreateSupplierRequest(BaseModel):
    supplier_id: str | None = None
    name: str
    channel: str | None = None
    external_user_id: str | None = None
    contact_name: str | None = None
    language_preference: str = "zh"
    region: str | None = None


@app.post("/api/m-side/suppliers")
def create_supplier_profile(request: CreateSupplierRequest):
    from src.m_side.supplier_profile import create_supplier_profile as _create
    profile = _create(
        supplier_id=request.supplier_id,
        name=request.name,
        channel=request.channel,
        external_user_id=request.external_user_id,
        contact_name=request.contact_name,
        language_preference=request.language_preference,
        region=request.region,
    )
    return profile.model_dump(mode="json")


@app.get("/api/m-side/suppliers/{supplier_id}")
def get_supplier_profile(supplier_id: str):
    from src.m_side.supplier_profile import get_supplier_profile as _get
    profile = _get(supplier_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return profile.model_dump(mode="json")


class BindChannelRequest(BaseModel):
    channel: str
    external_user_id: str


@app.post("/api/m-side/suppliers/{supplier_id}/bind-channel")
def bind_supplier_channel(supplier_id: str, request: BindChannelRequest):
    from src.m_side.supplier_identity import bind_supplier_channel as _bind
    try:
        profile = _bind(supplier_id, request.channel, request.external_user_id)
        return profile.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── B+M Bridge endpoints ──────────────────────────────────────────────────────

class DispatchInquiryRequest(BaseModel):
    b_workspace_id: str
    supplier_ids: list[str]
    channel: str = "mock"


@app.post("/api/bm/dispatch-inquiry")
def dispatch_inquiry_to_suppliers(request: DispatchInquiryRequest):
    from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
    try:
        contexts = dispatch_supplier_inquiry(
            request.b_workspace_id,
            request.supplier_ids,
            request.channel,
        )
        return {"ok": True, "dispatched": [c.model_dump(mode="json") for c in contexts]}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


class PushResponseRequest(BaseModel):
    m_workspace_id: str


@app.post("/api/bm/push-response-to-b-side")
def push_response_to_b_side(request: PushResponseRequest):
    from src.m_side.supplier_workspace import get_m_workspace
    from src.bm_bridge.response_bridge import push_supplier_response_to_b_side
    try:
        workspace = get_m_workspace(request.m_workspace_id)
        if workspace.response_packet is None:
            raise HTTPException(status_code=400, detail="No response packet in workspace")
        result = push_supplier_response_to_b_side(workspace.response_packet)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class CreateOrderExecutionRequest(BaseModel):
    b_workspace_id: str
    selected_path_id: str


@app.post("/api/bm/create-order-execution")
def create_order_execution(request: CreateOrderExecutionRequest):
    from src.bm_bridge.order_bridge import create_order_execution_from_selected_path
    try:
        order = create_order_execution_from_selected_path(
            request.b_workspace_id,
            request.selected_path_id,
        )
        return order.model_dump(mode="json")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── M-side workspace endpoints ────────────────────────────────────────────────

@app.get("/api/m-side/workspaces/{m_workspace_id}")
def get_m_side_workspace(m_workspace_id: str):
    from src.m_side.supplier_workspace import get_m_workspace
    try:
        workspace = get_m_workspace(m_workspace_id)
        return workspace.model_dump(mode="json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace {m_workspace_id} not found")


class SupplierMessageRequest(BaseModel):
    text: str
    attachments: list[dict] = []


@app.post("/api/m-side/workspaces/{m_workspace_id}/message")
def submit_supplier_message(m_workspace_id: str, request: SupplierMessageRequest):
    from src.m_side.response_collector import append_supplier_message
    try:
        workspace = append_supplier_message(m_workspace_id, request.text, request.attachments)
        return {"ok": True, "status": workspace.status, "message_count": len(workspace.raw_supplier_messages)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace {m_workspace_id} not found")


@app.post("/api/m-side/workspaces/{m_workspace_id}/normalize-response")
def normalize_supplier_response(m_workspace_id: str):
    from src.m_side.response_collector import build_response_packet_from_messages
    from src.openclaw_skill.m_side_response_formatter import format_response_packet_preview
    try:
        packet = build_response_packet_from_messages(m_workspace_id)
        return {"ok": True, "preview": format_response_packet_preview(packet)}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/m-side/workspaces/{m_workspace_id}/submit-response")
def submit_response_to_b_side(m_workspace_id: str):
    from src.m_side.supplier_workspace import get_m_workspace
    from src.bm_bridge.response_bridge import push_supplier_response_to_b_side
    try:
        workspace = get_m_workspace(m_workspace_id)
        if workspace.response_packet is None:
            raise HTTPException(status_code=400, detail="No response packet built yet")
        result = push_supplier_response_to_b_side(workspace.response_packet)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── M-side order execution endpoints ─────────────────────────────────────────

class AcknowledgeOrderRequest(BaseModel):
    message: str = "确认接单"


@app.post("/api/m-side/orders/{order_execution_id}/acknowledge")
def acknowledge_order_endpoint(order_execution_id: str, request: AcknowledgeOrderRequest):
    from src.m_side.order_acknowledger import acknowledge_order
    try:
        order = acknowledge_order(order_execution_id, request.message)
        return {"ok": True, "status": order.status}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order {order_execution_id} not found")


class ProductionUpdateRequest(BaseModel):
    supplier_id: str
    message: str
    attachments: list[dict] = []


@app.post("/api/m-side/orders/{order_execution_id}/production-update")
def production_update_endpoint(order_execution_id: str, request: ProductionUpdateRequest):
    from src.m_side.production_update import submit_production_update
    update = submit_production_update(
        order_execution_id, request.supplier_id, request.message, request.attachments
    )
    return {"ok": True, "update_id": update.update_id, "status": update.status}


class QCUpdateRequest(BaseModel):
    supplier_id: str
    message: str
    attachments: list[dict] = []


@app.post("/api/m-side/orders/{order_execution_id}/qc-update")
def qc_update_endpoint(order_execution_id: str, request: QCUpdateRequest):
    from src.m_side.qc_update import submit_qc_update
    qc = submit_qc_update(
        order_execution_id, request.supplier_id, request.message, request.attachments
    )
    return {"ok": True, "qc_update_id": qc.qc_update_id, "qc_status": qc.qc_status}


class LogisticsUpdateRequest(BaseModel):
    supplier_id: str
    message: str


@app.post("/api/m-side/orders/{order_execution_id}/logistics-update")
def logistics_update_endpoint(order_execution_id: str, request: LogisticsUpdateRequest):
    from src.m_side.logistics_update import submit_logistics_update
    lgs = submit_logistics_update(
        order_execution_id, request.supplier_id, request.message
    )
    return {
        "ok": True,
        "logistics_update_id": lgs.logistics_update_id,
        "status": lgs.status,
        "tracking_number": lgs.tracking_number,
    }


class ExceptionReportRequest(BaseModel):
    supplier_id: str
    message: str
    order_execution_id: str | None = None


@app.post("/api/m-side/workspaces/{m_workspace_id}/exception")
def report_exception_endpoint(m_workspace_id: str, request: ExceptionReportRequest):
    from src.m_side.exception_handler import submit_exception_report
    exc = submit_exception_report(
        m_workspace_id, request.supplier_id, request.message, request.order_execution_id
    )
    return {
        "ok": True,
        "exception_id": exc.exception_id,
        "severity": exc.severity,
        "category": exc.category,
    }


# ─── Role-switching M-side procurement routes ──────────────────────────────────

class ResolveRoleRequest(BaseModel):
    actor_id: str
    original_buyer_actor_id: str
    main_supplier_actor_id: str | None = None
    edge_id: str | None = None
    edge_type: str | None = None
    counterparty_actor_id: str | None = None


@app.post("/api/projects/{project_id}/resolve-role")
def resolve_role_endpoint(project_id: str, request: ResolveRoleRequest):
    """Resolve the contextual role of an actor within a project edge."""
    from src.actors.role_resolver import resolve_role_context
    rc = resolve_role_context(
        project_id=project_id,
        actor_id=request.actor_id,
        original_buyer_actor_id=request.original_buyer_actor_id,
        main_supplier_actor_id=request.main_supplier_actor_id,
        edge_id=request.edge_id,
        edge_type=request.edge_type,
        counterparty_actor_id=request.counterparty_actor_id,
    )
    return rc.model_dump()


class PlanDependenciesRequest(BaseModel):
    product_summary: str
    category: str
    quantity: int | None = None
    main_supplier_actor_id: str
    candidate_fabric_ids: list[str] = []
    candidate_trim_ids: list[str] = []
    candidate_packaging_ids: list[str] = []
    candidate_qc_ids: list[str] = []
    candidate_logistics_ids: list[str] = []
    destination: str | None = None


@app.post("/api/m-side/{project_id}/plan-dependencies")
def plan_dependencies_endpoint(project_id: str, request: PlanDependenciesRequest):
    """Plan upstream dependencies for a project."""
    from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies
    from src.m_side.upstream.upstream_store import store_dependencies
    deps = plan_upstream_dependencies(
        project_id=project_id,
        product_summary=request.product_summary,
        category=request.category,
        quantity=request.quantity,
        main_supplier_actor_id=request.main_supplier_actor_id,
        candidate_fabric_ids=request.candidate_fabric_ids or None,
        candidate_trim_ids=request.candidate_trim_ids or None,
        candidate_packaging_ids=request.candidate_packaging_ids or None,
        candidate_qc_ids=request.candidate_qc_ids or None,
        candidate_logistics_ids=request.candidate_logistics_ids or None,
        destination=request.destination,
    )
    deps_data = [d.model_dump() for d in deps]
    store_dependencies(project_id, deps_data)
    return {"project_id": project_id, "dependencies": deps_data}


class BuildUpstreamInquiryRequest(BaseModel):
    dependency_id: str
    upstream_actor_id: str
    main_supplier_actor_id: str
    quantity: int | None = None
    # allow passing dependency inline if not stored yet
    dependency_type: str | None = None
    description: str | None = None
    required_specs: dict = {}


@app.post("/api/m-side/{project_id}/upstream-inquiries")
def build_upstream_inquiries_endpoint(project_id: str, request: BuildUpstreamInquiryRequest):
    """Build and store an upstream inquiry for a dependency."""
    from src.m_side.dependencies.dependency_planner import DependencyNeed
    from src.m_side.upstream.inquiry_builder import build_upstream_inquiry
    from src.m_side.upstream.upstream_store import load_dependencies, store_inquiry

    # Look up dependency from store or construct from inline params
    dep = None
    for d in load_dependencies(project_id):
        if d.get("dependency_id") == request.dependency_id:
            dep = DependencyNeed.model_validate(d)
            break

    if dep is None:
        if not request.dependency_type:
            raise HTTPException(status_code=404,
                                detail=f"Dependency {request.dependency_id} not found for project {project_id}. "
                                       "Call plan-dependencies first or provide dependency_type.")
        dep = DependencyNeed(
            dependency_id=request.dependency_id,
            project_id=project_id,
            dependency_type=request.dependency_type,  # type: ignore[arg-type]
            description=request.description or request.dependency_type,
            required_specs=request.required_specs,
        )

    inquiry = build_upstream_inquiry(
        dependency=dep,
        upstream_actor_id=request.upstream_actor_id,
        main_supplier_actor_id=request.main_supplier_actor_id,
        quantity=request.quantity,
    )
    store_inquiry(project_id, inquiry.model_dump())
    return inquiry.model_dump()


class DispatchUpstreamInquiryRequest(BaseModel):
    channel: str = "mock"
    project_id: str | None = None


@app.post("/api/m-side/upstream/{inquiry_id}/dispatch")
def dispatch_upstream_inquiry_endpoint(inquiry_id: str, request: DispatchUpstreamInquiryRequest):
    """Dispatch a stored upstream inquiry via the specified channel."""
    from src.m_side.upstream.inquiry_builder import UpstreamInquiry
    from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry
    from src.m_side.upstream.upstream_store import load_inquiries

    # Search across project if project_id provided, else scan all
    inquiry_data = None
    if request.project_id:
        from src.m_side.upstream.upstream_store import load_inquiry
        inquiry_data = load_inquiry(request.project_id, inquiry_id)
    else:
        # Scan data/upstream/* directories
        import os
        base = __import__("pathlib").Path("data/upstream")
        if base.exists():
            for proj_dir in base.iterdir():
                if proj_dir.is_dir():
                    from src.m_side.upstream.upstream_store import load_inquiry
                    found = load_inquiry(proj_dir.name, inquiry_id)
                    if found:
                        inquiry_data = found
                        break

    if inquiry_data is None:
        raise HTTPException(status_code=404, detail=f"Inquiry {inquiry_id} not found")

    inquiry = UpstreamInquiry.model_validate(inquiry_data)
    result = dispatch_upstream_inquiry(
        inquiry=inquiry,
        channel=request.channel,  # type: ignore[arg-type]
    )
    return result.model_dump()


class SubmitUpstreamResponseRequest(BaseModel):
    raw_message: str
    upstream_actor_id: str
    project_id: str


@app.post("/api/m-side/upstream/{inquiry_id}/responses")
def submit_upstream_response_endpoint(inquiry_id: str, request: SubmitUpstreamResponseRequest):
    """Parse a raw upstream supplier response and store it."""
    from src.m_side.upstream.inquiry_builder import UpstreamInquiry
    from src.m_side.upstream.response_parser import parse_upstream_response
    from src.m_side.upstream.upstream_store import load_inquiry, store_response

    inquiry_data = load_inquiry(request.project_id, inquiry_id)
    if inquiry_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Inquiry {inquiry_id} not found in project {request.project_id}")

    inquiry = UpstreamInquiry.model_validate(inquiry_data)
    parsed = parse_upstream_response(
        raw_message=request.raw_message,
        inquiry_id=inquiry_id,
        project_id=request.project_id,
        upstream_actor_id=request.upstream_actor_id,
        dependency_id=inquiry.dependency_id,
        dependency_type=inquiry.dependency_type,
    )
    store_response(request.project_id, parsed.model_dump())
    return parsed.model_dump()


@app.get("/api/m-side/{project_id}/upstream-options")
def get_upstream_options_endpoint(project_id: str, dependency_id: str | None = None):
    """Generate or retrieve upstream options for a project's dependencies."""
    from src.m_side.upstream.response_parser import UpstreamResponse
    from src.m_side.upstream.option_engine import generate_upstream_options
    from src.m_side.upstream.upstream_store import (
        load_dependencies, load_responses_for_dependency,
        load_options, store_options,
    )
    from src.projects.project_graph import get_project

    try:
        project = get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    main_supplier = project.main_supplier_actor_id or "unknown"
    deps = load_dependencies(project_id)
    if dependency_id:
        deps = [d for d in deps if d.get("dependency_id") == dependency_id]

    all_options: list[dict] = []
    for dep in deps:
        dep_id = dep["dependency_id"]
        dep_type = dep["dependency_type"]
        resp_data = load_responses_for_dependency(project_id, dep_id)
        if not resp_data:
            continue
        responses = [UpstreamResponse.model_validate(r) for r in resp_data]
        opts = generate_upstream_options(
            project_id=project_id,
            dependency_id=dep_id,
            dependency_type=dep_type,
            responses=responses,
            main_supplier_actor_id=main_supplier,
        )
        opts_data = [o.model_dump() for o in opts]
        store_options(project_id, opts_data)
        all_options.extend(opts_data)

    return {"project_id": project_id, "options": all_options}


class ApproveUpstreamOptionRequest(BaseModel):
    approval_request_id: str | None = None
    option_id: str
    approved_by: str
    mode: str = "human"
    notes: str = ""
    # allow creating approval request inline
    dependency_id: str | None = None
    dependency_type: str | None = None


@app.post("/api/m-side/{project_id}/approve-upstream-option")
def approve_upstream_option_endpoint(project_id: str, request: ApproveUpstreamOptionRequest):
    """Approve an upstream option (create approval request if needed, then approve)."""
    from src.m_side.upstream.option_engine import UpstreamOption
    from src.m_side.upstream.approval_gate import (
        request_upstream_option_approval, approve_upstream_option,
    )
    from src.m_side.upstream.upstream_store import (
        load_option, load_options, load_approval_request,
        store_approval_request, update_approval_request,
    )

    # Find the option
    option_data = load_option(project_id, request.option_id)
    if option_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Option {request.option_id} not found in project {project_id}")
    option = UpstreamOption.model_validate(option_data)

    # Find or create approval request
    approval_req = None
    if request.approval_request_id:
        req_data = load_approval_request(project_id, request.approval_request_id)
        if req_data is None:
            raise HTTPException(status_code=404,
                                detail=f"Approval request {request.approval_request_id} not found")
        from src.m_side.upstream.approval_gate import ApprovalRequest
        approval_req = ApprovalRequest.model_validate(req_data)
    else:
        dep_id = request.dependency_id or option.dependency_id
        dep_type = request.dependency_type or option.dependency_type
        # Gather all options for this dependency
        all_opts = [UpstreamOption.model_validate(o) for o in load_options(project_id)
                    if o.get("dependency_id") == dep_id]
        if not all_opts:
            all_opts = [option]
        approval_req = request_upstream_option_approval(
            project_id=project_id,
            dependency_id=dep_id,
            dependency_type=dep_type,
            options=all_opts,
        )
        store_approval_request(project_id, approval_req.model_dump())

    result = approve_upstream_option(
        approval_request=approval_req,
        approved_option_id=request.option_id,
        approved_by=request.approved_by,
        mode=request.mode,  # type: ignore[arg-type]
        notes=request.notes,
    )

    # Persist approval result into the approval record
    update_approval_request(project_id, approval_req.approval_request_id, {
        "status": "approved",
        "approved_result": result.model_dump(),
    })

    return result.model_dump()


class GenerateRollupRequest(BaseModel):
    main_supplier_actor_id: str
    product_summary: str
    quantity: int | None = None
    main_capacity_available: bool = True
    main_capacity_note: str = "Internal capacity confirmed."
    unresolved_dependency_types: list[str] = []


@app.post("/api/m-side/{project_id}/rollup")
def generate_rollup_endpoint(project_id: str, request: GenerateRollupRequest):
    """Generate a SupplierResponseRollup from all approved upstream options."""
    from src.m_side.upstream.approval_gate import ApprovalResult
    from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup
    from src.m_side.upstream.upstream_store import load_approval_results, store_rollup

    approval_data = load_approval_results(project_id)
    if not approval_data:
        raise HTTPException(status_code=400,
                            detail="No approved upstream options found. Approve at least one option first.")

    approval_results = [ApprovalResult.model_validate(a) for a in approval_data]
    rollup = generate_supplier_response_rollup(
        project_id=project_id,
        main_supplier_actor_id=request.main_supplier_actor_id,
        approval_results=approval_results,
        product_summary=request.product_summary,
        quantity=request.quantity,
        main_capacity_available=request.main_capacity_available,
        main_capacity_note=request.main_capacity_note,
        unresolved_dependency_types=request.unresolved_dependency_types or None,
    )
    rollup_data = rollup.model_dump(mode="json")
    store_rollup(project_id, rollup_data)
    return rollup_data


class SubmitRollupRequest(BaseModel):
    b_workspace_id: str
    supplier_name: str = "Manufacturer M"


@app.post("/api/m-side/{project_id}/submit-rollup-to-b-side")
def submit_rollup_to_b_side_endpoint(project_id: str, request: SubmitRollupRequest):
    """Submit the generated rollup to the B-side workspace."""
    from src.m_side.rollup.supplier_response_rollup import SupplierResponseRollup
    from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side
    from src.m_side.upstream.upstream_store import load_rollup

    rollup_data = load_rollup(project_id)
    if rollup_data is None:
        raise HTTPException(status_code=400,
                            detail="No rollup found for this project. Call /rollup first.")

    rollup = SupplierResponseRollup.model_validate(rollup_data)
    result = submit_rollup_to_b_side(
        rollup=rollup,
        b_workspace_id=request.b_workspace_id,
        supplier_name=request.supplier_name,
    )
    return result.model_dump()
