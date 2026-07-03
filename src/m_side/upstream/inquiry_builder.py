"""
Upstream Inquiry Builder — generates structured bilingual inquiries to upstream suppliers.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from src.m_side.dependencies.dependency_planner import DependencyNeed
from src.m_side.m_event_logger import log_m_event


class UpstreamInquiry(BaseModel):
    inquiry_id: str
    project_id: str
    parent_main_supplier_actor_id: str
    upstream_actor_id: str
    dependency_id: str
    dependency_type: str
    message_text_en: str
    message_text_zh: str
    requested_fields: list[str] = Field(default_factory=list)
    required_reply_schema: dict = Field(default_factory=dict)
    due_time: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_FABRIC_FIELDS = [
    "can_supply",
    "fabric_type",
    "available_quantity",
    "moq",
    "price_per_meter",
    "currency",
    "color_options",
    "shrinkage_rate",
    "substitute_options",
    "earliest_dispatch_date",
    "lead_time_days",
    "can_meet_buyer_deadline",
    "quality_notes",
]

_TRIM_FIELDS = [
    "can_supply",
    "trim_type",
    "available_quantity",
    "moq",
    "unit_price",
    "currency",
    "color_options",
    "lead_time_days",
    "earliest_dispatch_date",
    "substitute_options",
    "quality_notes",
]

_PACKAGING_FIELDS = [
    "can_supply",
    "packaging_type",
    "available_quantity",
    "moq",
    "unit_price",
    "currency",
    "lead_time_days",
    "earliest_dispatch_date",
]

_QC_FIELDS = [
    "can_provide",
    "inspection_type",
    "available_dates",
    "price_per_piece",
    "currency",
    "lead_time_days",
    "turnaround_days",
]

_LOGISTICS_FIELDS = [
    "can_provide",
    "service_type",
    "destination",
    "estimated_transit_days",
    "price_per_carton",
    "currency",
    "earliest_pickup_date",
    "incoterms",
]


def _due_time(days: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _build_fabric_inquiry(dep: DependencyNeed, upstream_actor_id: str, quantity: int | None) -> tuple[str, str]:
    qty_str = f"{quantity} pcs" if quantity else "quantity TBD"
    en = (
        f"Hi, we have an order for {dep.description} ({qty_str}) and need fabric supply confirmation.\n\n"
        f"Please confirm:\n"
        f"1. Can you supply? What fabric type and weight?\n"
        f"2. Available stock quantity and MOQ?\n"
        f"3. Price per meter (USD/RMB) and currency?\n"
        f"4. Color options available?\n"
        f"5. Shrinkage rate / quality risk?\n"
        f"6. Any substitute options if primary is unavailable?\n"
        f"7. Earliest dispatch date?\n"
        f"8. Lead time (days from order to dispatch)?\n"
        f"9. Can you support the buyer deadline?\n\n"
        f"Please reply with structured information. Thank you."
    )
    zh = (
        f"您好，我们有一个订单需要确认面料供应：{dep.description}（数量：{qty_str}）。\n\n"
        f"请确认以下信息：\n"
        f"1. 能否供货？面料类型和克重？\n"
        f"2. 现有库存数量和最小起订量（MOQ）？\n"
        f"3. 每米价格（美元/人民币）及货币类型？\n"
        f"4. 可供颜色选项？\n"
        f"5. 缩水率 / 品质风险？\n"
        f"6. 如主材无货，是否有替代品？\n"
        f"7. 最早发货日期？\n"
        f"8. 从下单到发货的交货周期（天）？\n"
        f"9. 能否满足买家截止日期？\n\n"
        f"请提供结构化回复，谢谢。"
    )
    return en, zh


def _build_trim_inquiry(dep: DependencyNeed, upstream_actor_id: str, quantity: int | None) -> tuple[str, str]:
    qty_str = f"{quantity} sets" if quantity else "quantity TBD"
    en = (
        f"Hi, we need trim/button supply confirmation for {dep.description} ({qty_str}).\n\n"
        f"Please confirm:\n"
        f"1. Can you supply? Trim types available?\n"
        f"2. Available stock and MOQ?\n"
        f"3. Unit price and currency?\n"
        f"4. Color options?\n"
        f"5. Lead time (days)?\n"
        f"6. Earliest dispatch date?\n"
        f"7. Any substitute options?\n\n"
        f"Thank you."
    )
    zh = (
        f"您好，我们需要确认辅料/纽扣供应：{dep.description}（数量：{qty_str}）。\n\n"
        f"请确认：\n"
        f"1. 能否供货？可供辅料类型？\n"
        f"2. 现货库存和最小起订量？\n"
        f"3. 单价及货币？\n"
        f"4. 可供颜色？\n"
        f"5. 交货周期（天）？\n"
        f"6. 最早发货日期？\n"
        f"7. 是否有替代品？\n\n"
        f"谢谢。"
    )
    return en, zh


def _build_packaging_inquiry(dep: DependencyNeed, upstream_actor_id: str, quantity: int | None) -> tuple[str, str]:
    qty_str = f"{quantity} units" if quantity else "quantity TBD"
    en = (
        f"Hi, we need packaging supply confirmation for {dep.description} ({qty_str}).\n\n"
        f"Please confirm: packaging type, MOQ, unit price, lead time, earliest dispatch date.\n"
        f"Thank you."
    )
    zh = (
        f"您好，我们需要确认包装供应：{dep.description}（数量：{qty_str}）。\n\n"
        f"请确认：包装类型、最小起订量、单价、交货周期、最早发货日期。\n"
        f"谢谢。"
    )
    return en, zh


def _build_qc_inquiry(dep: DependencyNeed, upstream_actor_id: str, quantity: int | None) -> tuple[str, str]:
    qty_str = f"{quantity} pcs" if quantity else "quantity TBD"
    en = (
        f"Hi, we need QC inspection service for {dep.description} ({qty_str}).\n\n"
        f"Please confirm: inspection types offered, available dates, price per piece, "
        f"turnaround time, and any relevant certifications.\n"
        f"Thank you."
    )
    zh = (
        f"您好，我们需要质检服务：{dep.description}（数量：{qty_str}）。\n\n"
        f"请确认：检验类型、可用日期、每件价格、周转时间及相关认证。\n"
        f"谢谢。"
    )
    return en, zh


def _build_logistics_inquiry(dep: DependencyNeed, upstream_actor_id: str, quantity: int | None) -> tuple[str, str]:
    destination = dep.required_specs.get("destination", "TBD")
    qty_str = f"{quantity} pcs" if quantity else "quantity TBD"
    en = (
        f"Hi, we need logistics service for {dep.description} ({qty_str}) to {destination}.\n\n"
        f"Please confirm: service type, transit days, price per carton (USD), "
        f"earliest pickup date, and Incoterms.\n"
        f"Thank you."
    )
    zh = (
        f"您好，我们需要物流服务：{dep.description}（数量：{qty_str}），目的地：{destination}。\n\n"
        f"请确认：服务类型、在途天数、每箱价格（美元）、最早提货日期及贸易条款（Incoterms）。\n"
        f"谢谢。"
    )
    return en, zh


_FIELD_MAP = {
    "fabric": _FABRIC_FIELDS,
    "trim": _TRIM_FIELDS,
    "packaging": _PACKAGING_FIELDS,
    "qc_testing": _QC_FIELDS,
    "logistics": _LOGISTICS_FIELDS,
}

_BUILDER_MAP = {
    "fabric": _build_fabric_inquiry,
    "trim": _build_trim_inquiry,
    "packaging": _build_packaging_inquiry,
    "qc_testing": _build_qc_inquiry,
    "logistics": _build_logistics_inquiry,
}


def build_upstream_inquiry(
    dependency: DependencyNeed,
    upstream_actor_id: str,
    main_supplier_actor_id: str,
    quantity: int | None = None,
) -> UpstreamInquiry:
    dep_type = dependency.dependency_type
    builder = _BUILDER_MAP.get(dep_type)
    if builder:
        en, zh = builder(dependency, upstream_actor_id, quantity)
    else:
        en = f"Please confirm availability and pricing for: {dependency.description}"
        zh = f"请确认供货情况和价格：{dependency.description}"

    fields = _FIELD_MAP.get(dep_type, ["can_supply", "price", "lead_time_days", "moq"])

    inquiry = UpstreamInquiry(
        inquiry_id=f"UPQ-{uuid.uuid4().hex[:10].upper()}",
        project_id=dependency.project_id,
        parent_main_supplier_actor_id=main_supplier_actor_id,
        upstream_actor_id=upstream_actor_id,
        dependency_id=dependency.dependency_id,
        dependency_type=dep_type,
        message_text_en=en,
        message_text_zh=zh,
        requested_fields=fields,
        required_reply_schema={f: "string|number|boolean" for f in fields},
        due_time=_due_time(2),
    )

    log_m_event(
        event_type="UPSTREAM_INQUIRY_CREATED",
        b_workspace_id=dependency.project_id,
        supplier_id=main_supplier_actor_id,
        payload={
            "inquiry_id": inquiry.inquiry_id,
            "upstream_actor_id": upstream_actor_id,
            "dependency_type": dep_type,
            "dependency_id": dependency.dependency_id,
        },
    )

    return inquiry
