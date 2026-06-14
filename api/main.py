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
    action: str
    channel: str | None = None
    external_user_id: str | None = None
    params: dict = {}


@app.post("/api/skill/invoke")
def invoke_skill(request: SkillInvokeRequest):
    """OpenClaw skill invocation endpoint — routes to B-side or M-side handlers."""
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


# ─── Channel adapter endpoints ─────────────────────────────────────────────────

class ChannelWebhookRequest(BaseModel):
    payload: dict = {}
    headers: dict = {}


@app.post("/api/channels/{channel}/webhook")
def channel_webhook(channel: str, request: ChannelWebhookRequest):
    """Receive a provider webhook, verify signature, normalize, and route."""
    from src.channels.router import route_inbound_message, _get_adapter
    from src.channels.channel_event_logger import log_channel_event

    adapter = _get_adapter(channel)

    # Signature verification
    if not adapter.verify_signature(request.headers, request.payload):
        log_channel_event(
            "CHANNEL_SIGNATURE_VERIFICATION_FAILED",
            {"channel": channel, "headers": request.headers},
        )
        raise HTTPException(status_code=403, detail="Signature verification failed")

    log_channel_event("CHANNEL_INBOUND_MESSAGE_RECEIVED", {"channel": channel, "payload_keys": list(request.payload.keys())})

    msg = adapter.normalize_inbound(request.payload)
    log_channel_event("CHANNEL_MESSAGE_NORMALIZED", {"channel": channel, "idempotency_key": msg.idempotency_key, "intent": msg.intent})

    if msg.actor_id:
        log_channel_event("CHANNEL_ACTOR_RESOLVED", {"channel": channel, "actor_id": msg.actor_id})

    routing = route_inbound_message(msg)
    log_channel_event("CHANNEL_ROUTE_DECIDED", {"channel": channel, "route": routing["route"], "reason": routing["reason"]})

    return {
        "ok": True,
        "channel": channel,
        "external_user_id": msg.external_user_id,
        "idempotency_key": msg.idempotency_key,
        "intent": msg.intent,
        "routing": routing,
    }


class MockInboundRequest(BaseModel):
    external_user_id: str
    text: str
    external_thread_id: str | None = None
    attachments: list[dict] = []


@app.post("/api/channels/mock/inbound")
def mock_inbound(request: MockInboundRequest):
    """Simulate an inbound message via the mock adapter."""
    from src.channels.mock_adapter import MockAdapter
    from src.channels.router import route_inbound_message
    from src.channels.channel_event_logger import log_channel_event

    adapter = MockAdapter()
    payload = {
        "channel": "mock",
        "external_user_id": request.external_user_id,
        "external_thread_id": request.external_thread_id,
        "text": request.text,
        "attachments": request.attachments,
    }
    msg = adapter.normalize_inbound(payload)
    log_channel_event("CHANNEL_INBOUND_MESSAGE_RECEIVED", {"channel": "mock", "text": request.text})
    log_channel_event("CHANNEL_MESSAGE_NORMALIZED", {"channel": "mock", "idempotency_key": msg.idempotency_key, "intent": msg.intent})

    routing = route_inbound_message(msg)
    log_channel_event("CHANNEL_ROUTE_DECIDED", {"channel": "mock", "route": routing["route"]})

    return {
        "ok": True,
        "normalized": msg.model_dump(),
        "routing": routing,
    }


class EmailInboundRequest(BaseModel):
    payload: dict


@app.post("/api/channels/email/inbound")
def email_inbound(request: EmailInboundRequest):
    """Accept a parsed inbound email payload and normalize it."""
    from src.channels.email_adapter import EmailAdapter
    from src.channels.router import route_inbound_message
    from src.channels.channel_event_logger import log_channel_event

    adapter = EmailAdapter()
    msg = adapter.normalize_inbound(request.payload)
    log_channel_event("CHANNEL_INBOUND_MESSAGE_RECEIVED", {"channel": "email"})
    log_channel_event("CHANNEL_MESSAGE_NORMALIZED", {"channel": "email", "idempotency_key": msg.idempotency_key, "intent": msg.intent})

    routing = route_inbound_message(msg)
    log_channel_event("CHANNEL_ROUTE_DECIDED", {"channel": "email", "route": routing["route"]})

    return {
        "ok": True,
        "normalized": msg.model_dump(),
        "routing": routing,
    }


class SendMessageRequest(BaseModel):
    channel: str
    to_external_user_id: str
    to_external_thread_id: str | None = None
    text: str
    html: str | None = None
    subject: str | None = None
    attachments: list[dict] = []
    metadata: dict = {}


@app.post("/api/channels/send")
def send_channel_message(request: SendMessageRequest):
    """Send an outbound message via the specified channel adapter."""
    from src.channels.base import OutboundChannelMessage
    from src.channels.router import send_outbound_message
    from src.channels.channel_event_logger import log_channel_event

    msg = OutboundChannelMessage(
        channel=request.channel,
        to_external_user_id=request.to_external_user_id,
        to_external_thread_id=request.to_external_thread_id,
        text=request.text,
        html=request.html,
        subject=request.subject,
        attachments=request.attachments,
        metadata=request.metadata,
    )
    receipt = send_outbound_message(request.channel, msg)
    log_channel_event(
        "CHANNEL_OUTBOUND_MESSAGE_SENT",
        {"channel": request.channel, "to": request.to_external_user_id, "status": receipt.status},
    )
    log_channel_event(
        "CHANNEL_DELIVERY_RECEIPT_RECEIVED",
        {"channel": request.channel, "status": receipt.status, "message_id": receipt.message_id},
    )
    return {"ok": True, "receipt": receipt.model_dump()}
