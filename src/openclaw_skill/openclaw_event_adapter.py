"""
OpenClaw Event Adapter for Giraffe Agent.

Normalizes OpenClaw channel events and routes them to B-side or M-side
procurement workflows. OpenClaw owns all IM/Email/WeChat/WhatsApp/Telegram
channels. Giraffe owns procurement execution logic.

Supported channels (through the same normalized event shape):
  - openclaw-weixin (WeChat via OpenClaw)
  - openclaw-email  (Email via OpenClaw)
  - openclaw-whatsapp
  - openclaw-telegram

Giraffe never connects to WeChat, Email, or any IM channel directly.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from src.openclaw_skill.conversation_binding_store import (
    ConversationBinding,
    create_binding,
    find_binding,
    update_binding,
)
from src.openclaw_skill.message_draft_store import (
    MessageDraft,
    approve_draft,
    create_draft,
    find_pending_drafts as find_pending_message_drafts,
    reject_draft,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_evt_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


# ─── OpenClaw Event Model ──────────────────────────────────────────────────────

class OpenClawEvent(BaseModel):
    source: str = "openclaw"
    channel: str
    channel_account_id: str
    conversation_id: str
    sender_id: str
    sender_display_name: Optional[str] = None
    message_text: str = ""
    message_type: str = "text"
    attachments: list = Field(default_factory=list)
    timestamp: Optional[str] = None
    project_id: Optional[str] = None
    procurement_edge_id: Optional[str] = None
    actor_id: Optional[str] = None
    role_context: Optional[str] = None
    mode: Optional[str] = None  # b_side / m_side / auto / None → defaults to auto


# ─── Intent Detection ──────────────────────────────────────────────────────────

_APPROVAL_PHRASES = [
    "确认发送", "confirm send", "approve", "send it", "yes send",
    "confirmed", "go ahead", "please send", "ok send", "yes, send",
]

_REJECTION_PHRASES = [
    "取消", "不要发送", "reject", "do not send", "don't send",
    "cancel", "hold off", "no, don't send",
]

_BUYER_KEYWORDS = [
    "采购", "询价", "购买", "订购", "需要", "要", "帮我", "帮忙",
    "procurement", "inquiry", "purchase", "order", "sourcing",
    "rfq", "quotation", "quote", "buy", "need", "want",
    "衬衣", "衬衫", "t恤", "裤子", "外套", "帽子",
    "shirt", "t-shirt", "pants", "jacket", "hat", "garment",
    "产品", "商品", "零件", "部件",
]

_SUPPLIER_REPLY_KEYWORDS = [
    "可以做", "我们可以", "工厂可以", "能做", "能接", "报价",
    "we can", "we are able", "can produce", "can make", "our factory",
    "fob", "moq", "lead time", "交期", "单价", "最小起订量",
    "产能", "capacity", "usd", "price", "per pc", "per piece",
    "fabric", "gsm", "180gsm", "cotton", "material available",
]


def _is_approval(text: str) -> bool:
    tl = text.strip().lower()
    return any(phrase in tl for phrase in _APPROVAL_PHRASES)


def _is_rejection(text: str) -> bool:
    tl = text.strip().lower()
    return any(phrase in tl for phrase in _REJECTION_PHRASES)


def _detect_buyer_intent(text: str) -> bool:
    tl = text.lower()
    return any(kw in tl for kw in _BUYER_KEYWORDS)


def _detect_supplier_reply_intent(text: str) -> bool:
    tl = text.lower()
    return any(kw in tl for kw in _SUPPLIER_REPLY_KEYWORDS)


def _detect_mode_from_intent(text: str) -> str:
    """Infer b_side or m_side from message content."""
    if _detect_supplier_reply_intent(text):
        return "m_side"
    if _detect_buyer_intent(text):
        return "b_side"
    return "b_side"  # Default to b_side for ambiguous messages


# ─── Requirement Parsing Extensions for Chinese/Apparel ───────────────────────

def _parse_quantity_zh(text: str) -> Optional[int]:
    patterns = [
        r"(\d[\d,]*)\s*(?:件|个|pcs|pieces|units|套)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    return None


def _parse_destination_zh(text: str) -> Optional[str]:
    destination_map = {
        "温哥华": "Vancouver",
        "多伦多": "Toronto",
        "纽约": "New York",
        "洛杉矶": "Los Angeles",
        "上海": "Shanghai",
        "深圳": "Shenzhen",
        "广州": "Guangzhou",
        "北京": "Beijing",
        "伦敦": "London",
        "巴黎": "Paris",
        "东京": "Tokyo",
        "新加坡": "Singapore",
        "香港": "Hong Kong",
        "慕尼黑": "Munich",
    }
    for zh, en in destination_map.items():
        if zh in text:
            return en
    standard_cities = [
        "Vancouver", "Toronto", "New York", "Los Angeles",
        "Shanghai", "Shenzhen", "Guangzhou", "Beijing",
        "London", "Paris", "Munich", "Tokyo", "Singapore", "Hong Kong",
    ]
    tl = text.lower()
    for city in standard_cities:
        if city.lower() in tl:
            return city
    return None


def _parse_deadline_zh(text: str) -> Optional[str]:
    # "45 天内" / "within 45 days"
    m = re.search(r"(\d+)\s*天内", text)
    if m:
        return f"within {m.group(1)} days"
    m = re.search(r"within\s+(\d+)\s*days?", text, re.IGNORECASE)
    if m:
        return f"within {m.group(1)} days"
    # Date patterns
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"before\s+([A-Za-z]+\s+\d{1,2}(?:,?\s*\d{4})?)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _parse_material_zh(text: str) -> Optional[str]:
    tl = text.lower()
    materials = [
        ("纯棉", "cotton"), ("棉", "cotton"), ("cotton", "cotton"),
        ("polyester", "polyester"), ("涤纶", "polyester"),
        ("尼龙", "nylon"), ("nylon", "nylon"),
        ("铝", "aluminum"), ("aluminum", "aluminum"), ("aluminium", "aluminum"),
        ("钢", "steel"), ("steel", "steel"),
        ("塑料", "plastic"), ("abs", "ABS"),
    ]
    for zh_kw, en_name in materials:
        if zh_kw in tl:
            return en_name
    return None


def _parse_missing_fields_apparel(text: str, specs: dict) -> list[str]:
    """Detect missing apparel fields from Chinese procurement text."""
    missing = []
    tl = text.lower()

    if "尺码比例" not in text and "size ratio" not in tl and "size_ratio" not in specs:
        missing.append("size_ratio")
    if "克重" not in text and "gsm" not in tl and "fabric_weight" not in specs:
        missing.append("fabric_weight")
    if "包装" not in text and "packaging" not in tl and "packaging" not in specs:
        missing.append("packaging")
    if "目标单价" not in text and "target price" not in tl and "unit_price" not in tl \
            and "target_unit_price" not in specs:
        missing.append("target_unit_price")
    return missing


def _extract_specs_from_followup(text: str) -> dict:
    """Extract spec fields provided in a follow-up message."""
    specs: dict = {}

    # Size ratio e.g. "S 20%, M 40%, L 30%, XL 10%"
    size_m = re.findall(r"([SMLXL]+)\s+(\d+)%", text, re.IGNORECASE)
    if size_m:
        specs["size_ratio"] = {s: f"{p}%" for s, p in size_m}

    # GSM e.g. "180gsm"
    gsm_m = re.search(r"(\d+)\s*gsm", text, re.IGNORECASE)
    if gsm_m:
        specs["fabric_weight"] = f"{gsm_m.group(1)}gsm"

    # Target unit price
    price_m = re.search(r"(?:目标单价|单件目标价|target price|unit price)[^\d]*(\d+(?:\.\d+)?)\s*(?:美元|usd|\$)", text, re.IGNORECASE)
    if price_m:
        specs["target_unit_price"] = f"USD {price_m.group(1)}"
    elif re.search(r"(\d+(?:\.\d+)?)\s*(?:美元|usd|\$)", text, re.IGNORECASE):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:美元|usd|\$)", text, re.IGNORECASE)
        if m:
            specs["target_unit_price"] = f"USD {m.group(1)}"

    # Packaging
    if "纸箱" in text or "carton" in text.lower():
        specs["packaging"] = "carton"
    elif "袋" in text or "bag" in text.lower():
        specs["packaging"] = "bag"

    return specs


# ─── Missing Field Detection ───────────────────────────────────────────────────

def _build_missing_fields_reply(project_id: str, req_text: str, specs: dict,
                                 quantity: Optional[int], destination: Optional[str],
                                 deadline: Optional[str], material: Optional[str]) -> tuple[str, list[str]]:
    """Build the missing_fields reply text and list."""
    identified_lines = []
    if quantity:
        identified_lines.append(f"数量：{quantity} 件")
    if destination:
        identified_lines.append(f"目的地：{destination}")
    if deadline:
        identified_lines.append(f"目标交期：{deadline}")
    if material:
        identified_lines.append(f"面料/材料：{material}")
    if specs.get("fabric_weight"):
        identified_lines.append(f"面料克重：{specs['fabric_weight']}")
    if specs.get("size_ratio"):
        identified_lines.append(f"尺码比例：{specs['size_ratio']}")
    if specs.get("target_unit_price"):
        identified_lines.append(f"目标单价：{specs['target_unit_price']}")
    if specs.get("packaging"):
        identified_lines.append(f"包装方式：{specs['packaging']}")

    # Detect category for product name
    product_name = "采购商品"
    tl = req_text.lower()
    if "衬衣" in req_text or "衬衫" in req_text or "shirt" in tl:
        product_name = "白色纯棉衬衣" if "白色" in req_text or "white" in tl else "衬衣"
    elif "t恤" in req_text or "t-shirt" in tl:
        product_name = "T恤"

    missing_apparel = _parse_missing_fields_apparel(req_text, specs)
    missing_basic = []
    if not quantity:
        missing_basic.append("quantity")
    if not destination:
        missing_basic.append("destination")
    if not deadline:
        missing_basic.append("deadline")
    missing = missing_basic + [f for f in missing_apparel if f not in missing_basic]

    identified_block = "\n".join(identified_lines) if identified_lines else "(无法识别)"
    missing_labels = {
        "quantity": "数量",
        "destination": "目的地",
        "deadline": "目标交期",
        "material": "面料/材料",
        "size_ratio": "尺码比例",
        "fabric_weight": "面料克重",
        "packaging": "包装方式",
        "target_unit_price": "目标单价",
    }
    if missing:
        missing_block = "\n".join(
            f"{i + 1}. {missing_labels.get(f, f)}" for i, f in enumerate(missing)
        )
        reply_text = (
            f"已创建采购项目 {project_id}。\n\n"
            f"已识别：\n产品：{product_name}\n{identified_block}\n\n"
            f"还缺：\n{missing_block}"
        )
    else:
        reply_text = (
            f"采购项目 {project_id} 信息已齐全。\n\n"
            f"已识别：\n产品：{product_name}\n{identified_block}"
        )
    return reply_text, missing


# ─── B-side Handler ────────────────────────────────────────────────────────────

def _handle_b_side_new(event: OpenClawEvent, evt_id: str) -> dict:
    """Handle new B-side procurement project creation."""
    from src.b_side.workspace import create_b_workspace, get_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement

    workspace = create_b_workspace(event.message_text)
    req = structure_requirement(workspace.b_workspace_id, event.message_text)

    # Extend parsing with Chinese/apparel-specific field detection not in the base structurer
    quantity = req.quantity or _parse_quantity_zh(event.message_text)
    destination = req.destination or _parse_destination_zh(event.message_text)
    deadline = req.deadline or _parse_deadline_zh(event.message_text)
    material = req.material or _parse_material_zh(event.message_text)

    # Save extended fields back to requirement so follow-up messages can load them
    if quantity:
        req.quantity = quantity
    if destination:
        req.destination = destination
    if deadline:
        req.deadline = deadline
    if material:
        req.material = material

    extra_specs = _extract_specs_from_followup(event.message_text)
    if extra_specs:
        req.specs_json.update(extra_specs)

    workspace.buyer_requirement = req
    workspace.status = "requirement_structured"
    save_b_workspace(workspace)

    project_id = workspace.rfq_id
    reply_text, missing = _build_missing_fields_reply(
        project_id, event.message_text, req.specs_json,
        quantity, destination, deadline, material
    )

    binding = create_binding(
        source=event.source,
        channel=event.channel,
        channel_account_id=event.channel_account_id,
        conversation_id=event.conversation_id,
        sender_id=event.sender_id,
        sender_display_name=event.sender_display_name,
        project_id=project_id,
        b_workspace_id=workspace.b_workspace_id,
        mode="b_side",
        counterparty_type="customer",
    )

    status = "missing_fields" if missing else "requirement_complete"

    # If no missing fields, generate supplier inquiry draft
    draft_data = []
    approval_required = False
    if not missing:
        draft_text = _build_supplier_inquiry_draft(req, project_id, event.channel)
        draft = create_draft(
            project_id=project_id,
            b_workspace_id=workspace.b_workspace_id,
            channel=event.channel,
            target_role="supplier",
            draft_text=draft_text,
        )
        draft_data = [{
            "draft_id": draft.id,
            "target_role": "supplier",
            "channel": event.channel,
            "target_peer_id": None,
            "draft_text": draft_text,
        }]
        approval_required = True
        status = "draft_ready"
        reply_text = (
            f"我已生成供应商询价草稿，项目编号 {project_id}。请确认是否发送。\n\n回复：确认发送"
        )

    return {
        "ok": True,
        "project_id": project_id,
        "b_workspace_id": workspace.b_workspace_id,
        "mode": "b_side",
        "status": status,
        "reply_text": reply_text,
        "missing_fields": missing,
        "approval_required": approval_required,
        "message_drafts": draft_data,
        "outbound_messages": [],
        "execution_event_id": evt_id,
        "conversation_binding_id": binding.id,
    }


def _handle_b_side_followup(event: OpenClawEvent, binding: ConversationBinding, evt_id: str) -> dict:
    """Handle follow-up message to existing B-side project."""
    from src.b_side.workspace import get_b_workspace, save_b_workspace

    b_workspace_id = binding.b_workspace_id
    project_id = binding.project_id

    try:
        workspace = get_b_workspace(b_workspace_id)
    except FileNotFoundError:
        return {
            "ok": False,
            "error": f"Workspace {b_workspace_id} not found",
            "execution_event_id": evt_id,
        }

    req = workspace.buyer_requirement

    # Update specs from follow-up message
    extra_specs = _extract_specs_from_followup(event.message_text)
    if req and extra_specs:
        req.specs_json.update(extra_specs)
        workspace.buyer_requirement = req

    # Update destination / deadline if found
    extra_dest = _parse_destination_zh(event.message_text)
    extra_deadline = _parse_deadline_zh(event.message_text)
    extra_qty = _parse_quantity_zh(event.message_text)
    extra_material = _parse_material_zh(event.message_text)
    if req:
        if extra_dest and not req.destination:
            req.destination = extra_dest
        if extra_deadline and not req.deadline:
            req.deadline = extra_deadline
        if extra_qty and not req.quantity:
            req.quantity = extra_qty
        if extra_material and not req.material:
            req.material = extra_material
        workspace.buyer_requirement = req

    workspace.status = "requirement_structured"
    save_b_workspace(workspace)

    quantity = req.quantity if req else _parse_quantity_zh(event.message_text)
    destination = req.destination if req else _parse_destination_zh(event.message_text)
    deadline = req.deadline if req else _parse_deadline_zh(event.message_text)
    material = req.material if req else _parse_material_zh(event.message_text)
    specs = req.specs_json if req else extra_specs

    reply_text, missing = _build_missing_fields_reply(
        project_id, event.message_text, specs,
        quantity, destination, deadline, material
    )

    # Check for existing pending drafts first
    pending = find_pending_message_drafts(project_id)

    draft_data = []
    approval_required = False
    status = "missing_fields" if missing else "requirement_updated"

    if not missing:
        draft_text = _build_supplier_inquiry_draft(req, project_id, event.channel)
        draft = create_draft(
            project_id=project_id,
            b_workspace_id=b_workspace_id,
            channel=event.channel,
            target_role="supplier",
            draft_text=draft_text,
        )
        draft_data = [{
            "draft_id": draft.id,
            "target_role": "supplier",
            "channel": event.channel,
            "target_peer_id": None,
            "draft_text": draft_text,
        }]
        approval_required = True
        status = "draft_ready"
        reply_text = (
            f"已更新采购项目 {project_id}，信息已完整。\n"
            "我已生成供应商询价草稿。请确认是否发送。\n\n回复：确认发送"
        )

    return {
        "ok": True,
        "project_id": project_id,
        "b_workspace_id": b_workspace_id,
        "mode": "b_side",
        "status": status,
        "reply_text": reply_text,
        "missing_fields": missing,
        "approval_required": approval_required,
        "message_drafts": draft_data,
        "outbound_messages": [],
        "execution_event_id": evt_id,
    }


def _build_supplier_inquiry_draft(req, project_id: str, channel: str) -> str:
    lines = [
        "您好，",
        "",
        "我们有以下采购需求，请协助报价：",
        "",
        f"项目编号：{project_id}",
    ]
    if req:
        if req.quantity:
            lines.append(f"数量：{req.quantity} 件")
        if req.material:
            lines.append(f"面料/材料：{req.material}")
        if req.specs_json.get("fabric_weight"):
            lines.append(f"克重：{req.specs_json['fabric_weight']}")
        if req.specs_json.get("size_ratio"):
            lines.append(f"尺码比例：{req.specs_json['size_ratio']}")
        if req.destination:
            lines.append(f"目的地：{req.destination}")
        if req.deadline:
            lines.append(f"目标交期：{req.deadline}")
        if req.specs_json.get("target_unit_price"):
            lines.append(f"目标单价：{req.specs_json['target_unit_price']}")
        if req.specs_json.get("packaging"):
            lines.append(f"包装方式：{req.specs_json['packaging']}")
        lines.append("")
        lines.append(f"产品：{req.raw_text[:100] if req.raw_text else '见附件'}")
    lines += [
        "",
        "请回复：",
        "1. 是否可以接单",
        "2. 报价（单价 / 总价 / MOQ）",
        "3. 预计交期",
        "4. 包装与物流条款",
        "5. 付款条件",
        "",
        "感谢！",
    ]
    return "\n".join(lines)


# ─── Approval / Rejection Handlers ────────────────────────────────────────────

def _handle_approval(event: OpenClawEvent, binding: Optional[ConversationBinding], evt_id: str) -> dict:
    """Handle draft approval message."""
    project_id = event.project_id or (binding.project_id if binding else None)
    if not project_id:
        return {
            "ok": False,
            "error": "Cannot approve draft: no project_id found. Please provide project context.",
            "execution_event_id": evt_id,
        }

    pending = find_pending_message_drafts(project_id)
    if not pending:
        return {
            "ok": True,
            "project_id": project_id,
            "mode": binding.mode if binding else "b_side",
            "status": "no_pending_drafts",
            "reply_text": "没有找到待审核的草稿。",
            "approval_required": False,
            "message_drafts": [],
            "outbound_messages": [],
            "execution_event_id": evt_id,
        }

    outbound = []
    for draft in pending:
        approved = approve_draft(draft.id, event.sender_id)
        if approved:
            outbound.append({
                "channel": draft.channel,
                "target_peer_id": draft.target_peer_id,
                "text": draft.draft_text,
            })

    return {
        "ok": True,
        "project_id": project_id,
        "mode": binding.mode if binding else "b_side",
        "status": "approved_for_dispatch",
        "reply_text": "已确认。请通过 OpenClaw 发送以下消息。",
        "approval_required": False,
        "message_drafts": [],
        "outbound_messages": outbound,
        "execution_event_id": evt_id,
    }


def _handle_rejection(event: OpenClawEvent, binding: Optional[ConversationBinding], evt_id: str) -> dict:
    """Handle draft rejection message."""
    project_id = event.project_id or (binding.project_id if binding else None)
    if not project_id:
        return {
            "ok": False,
            "error": "Cannot reject draft: no project_id found.",
            "execution_event_id": evt_id,
        }

    pending = find_pending_message_drafts(project_id)
    for draft in pending:
        reject_draft(draft.id)

    return {
        "ok": True,
        "project_id": project_id,
        "mode": binding.mode if binding else "b_side",
        "status": "draft_rejected",
        "reply_text": "已取消。草稿未发送。",
        "approval_required": False,
        "message_drafts": [],
        "outbound_messages": [],
        "execution_event_id": evt_id,
    }


# ─── M-side Handler ────────────────────────────────────────────────────────────

def _parse_supplier_response(message_text: str) -> tuple[dict, list[str]]:
    """Parse supplier reply message into structured fields. Returns (identified, missing)."""
    identified: dict = {}
    tl = message_text.lower()

    # Price: "USD 4.80/pc", "4.80 美元", "$4.80 per piece"
    price_m = re.search(r"(?:usd|us\$|\$)?\s*(\d+(?:\.\d+)?)\s*(?:/pc|/piece|per\s*pc|per\s*piece|元/件|美元/件)", tl)
    if price_m:
        identified["unit_price"] = f"USD {price_m.group(1)}"

    # Lead time: "38 days", "38 天"
    lt_m = re.search(r"(\d+)\s*(?:days?|天)", tl)
    if lt_m:
        identified["lead_time"] = f"{lt_m.group(1)} days"

    # GSM
    gsm_m = re.search(r"(\d+)\s*gsm", tl)
    if gsm_m:
        identified["fabric_weight"] = f"{gsm_m.group(1)}gsm"

    # MOQ
    moq_m = re.search(r"moq\s*(?:is|:)?\s*(\d+)", tl)
    if moq_m:
        identified["moq"] = moq_m.group(1)
    elif "moq ok" in tl or "moq no problem" in tl:
        identified["moq"] = "ok"

    # FOB / logistics
    fob_m = re.search(r"fob\s+(\w+)", tl)
    if fob_m:
        identified["logistics_terms"] = f"FOB {fob_m.group(1).title()}"

    # Missing fields after parsing
    missing = []
    if "unit_price" not in identified:
        missing.append("unit_price")
    if "lead_time" not in identified:
        missing.append("lead_time")
    if "moq" not in identified:
        missing.append("moq")
    if "packaging" not in identified and "packaging" not in tl and "包装" not in message_text:
        missing.append("packaging")
    if "payment_terms" not in identified and "payment" not in tl and "付款" not in message_text:
        missing.append("payment_terms")

    return identified, missing


def _handle_m_side(event: OpenClawEvent, project_id: Optional[str],
                   binding: Optional[ConversationBinding], evt_id: str) -> dict:
    """Handle M-side supplier reply from OpenClaw."""
    supplier_name = event.sender_display_name or event.sender_id

    # If no project_id, ask for clarification — do NOT create a B-side project
    if not project_id:
        return {
            "ok": True,
            "project_id": None,
            "mode": "m_side",
            "status": "clarification_needed",
            "reply_text": (
                f"收到来自 {supplier_name} 的消息，但无法确认对应的采购项目。\n\n"
                "请问您在回复哪个询盘？请提供项目编号或询盘编号。"
            ),
            "missing_fields": ["project_id"],
            "approval_required": False,
            "message_drafts": [],
            "outbound_messages": [],
            "execution_event_id": evt_id,
        }

    identified, missing = _parse_supplier_response(event.message_text)

    # Build identified fields text
    identified_lines = []
    label_map = {
        "unit_price": "单价",
        "lead_time": "交期",
        "fabric_weight": "面料克重",
        "moq": "最小起订量",
        "logistics_terms": "物流条款",
    }
    for field, value in identified.items():
        identified_lines.append(f"{label_map.get(field, field)}：{value}")

    missing_label_map = {
        "unit_price": "报价/单价",
        "lead_time": "交期",
        "moq": "最小起订量",
        "packaging": "包装方式",
        "payment_terms": "付款条件",
    }

    identified_text = "、".join(identified_lines) if identified_lines else "（暂无可识别字段）"
    missing_text = "、".join(missing_label_map.get(f, f) for f in missing) if missing else ""

    if missing_text:
        reply_text = (
            f"已收到 {supplier_name} 的回复，并更新供应商响应记录。"
            f"已识别：{identified_text}。仍缺：{missing_text}。"
        )
    else:
        reply_text = (
            f"已收到 {supplier_name} 的完整回复，并更新供应商响应记录。"
            f"已识别：{identified_text}。"
        )

    # Create/update binding for this supplier conversation
    if not binding:
        create_binding(
            source=event.source,
            channel=event.channel,
            channel_account_id=event.channel_account_id,
            conversation_id=event.conversation_id,
            sender_id=event.sender_id,
            sender_display_name=event.sender_display_name,
            project_id=project_id,
            procurement_edge_id=event.procurement_edge_id,
            mode="m_side",
            counterparty_type="supplier",
        )

    # Append to M-side workspace if available
    _append_to_m_workspace(project_id, event.message_text, supplier_name)

    return {
        "ok": True,
        "project_id": project_id,
        "mode": "m_side",
        "status": "supplier_response_received",
        "reply_text": reply_text,
        "identified_fields": identified,
        "missing_fields": missing,
        "approval_required": False,
        "message_drafts": [],
        "outbound_messages": [],
        "execution_event_id": evt_id,
    }


def _append_to_m_workspace(project_id: str, message_text: str, supplier_name: str) -> None:
    """Try to append supplier message to the matching M-side workspace."""
    from src.m_side.supplier_workspace import get_m_workspace
    from src.m_side.response_collector import append_supplier_message
    from pathlib import Path
    import json

    m_dir = Path("data/m_side_workspaces")
    if not m_dir.exists():
        return
    for path in m_dir.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("b_rfq_id") == project_id or data.get("project_id") == project_id:
                workspace = get_m_workspace(data["m_workspace_id"])
                append_supplier_message(workspace.m_workspace_id, message_text)
                return
        except Exception:
            pass


# ─── Variable-M / Trade Salesperson Role ──────────────────────────────────────

TRADE_SALESPERSON_ROLES = {
    "CUSTOMER_FACING_M_SIDE",
    "UPSTREAM_B_SIDE",
    "TRADE_MERCHANDISER",
}


def resolve_trade_salesperson_role(
    context: str,
    counterparty: str,
) -> str:
    """
    Resolve the contextual role of a trading company salesperson.

    context: 'customer_facing' | 'supplier_facing' | 'execution'
    counterparty: 'customer' | 'supplier' | 'factory'
    """
    if context == "customer_facing" or counterparty in ("customer", "buyer"):
        return "CUSTOMER_FACING_M_SIDE"
    if context == "supplier_facing" or counterparty in ("supplier", "factory", "manufacturer"):
        return "UPSTREAM_B_SIDE"
    if context == "execution":
        return "TRADE_MERCHANDISER"
    return "TRADE_MERCHANDISER"


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def adapt_openclaw_event(event_data: dict) -> dict:
    """
    Main entry point: normalize an OpenClaw channel event and route to the
    appropriate B-side or M-side procurement workflow.

    Returns a structured response suitable for OpenClaw to send back to the
    originating channel. Giraffe never sends WeChat, Email, or IM messages
    directly — only OpenClaw does.
    """
    evt_id = _new_evt_id()

    try:
        event = OpenClawEvent.model_validate(event_data)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Invalid OpenClaw event payload: {e}",
            "execution_event_id": evt_id,
        }

    # Resolve mode — default to auto
    mode = (event.mode or "auto").strip().lower()

    # Look up conversation binding first
    binding = None
    if not event.project_id:
        binding = find_binding(
            event.source,
            event.channel,
            event.channel_account_id,
            event.conversation_id,
            event.sender_id,
        )
        if binding:
            event_project_id = binding.project_id
        else:
            event_project_id = None
    else:
        event_project_id = event.project_id
        # Also try to find binding for context
        binding = find_binding(
            event.source,
            event.channel,
            event.channel_account_id,
            event.conversation_id,
            event.sender_id,
        )

    # Resolve mode from binding if still auto
    if mode == "auto" and binding:
        mode = binding.mode

    # Check for approval / rejection phrases first (before mode detection)
    if _is_approval(event.message_text):
        return _handle_approval(event, binding, evt_id)

    if _is_rejection(event.message_text):
        return _handle_rejection(event, binding, evt_id)

    # If mode is still auto, detect from message intent
    if mode == "auto":
        mode = _detect_mode_from_intent(event.message_text)

    # Route to appropriate handler
    if mode == "m_side":
        return _handle_m_side(event, event_project_id, binding, evt_id)
    else:
        # B-side workflow
        if binding and event_project_id:
            # Continue existing project
            return _handle_b_side_followup(event, binding, evt_id)
        else:
            # New B-side procurement project
            return _handle_b_side_new(event, evt_id)
