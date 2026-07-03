"""
Cainiao-like API request/response models.
Field names use adapter mapping so real API fields can be changed in config.
"""
from __future__ import annotations
from pydantic import BaseModel


# Adapter mapping: internal field → Cainiao-like API field (configurable for real API)
CAINIAO_FIELD_MAP = {
    "tracking_number": "mailNo",
    "carrier_code": "cpCode",
    "event_time": "timeStr",
    "status_code": "statusCode",
    "status_text": "status",
    "location": "desc",
    "description": "remark",
    "provider_event_id": "eventId",
}


class CainiaoLikeTrackingRequest(BaseModel):
    tracking_number: str
    carrier_code: str | None = None
    app_key: str = ""
    sign: str = ""


class CainiaoLikeTrackingEvent(BaseModel):
    provider_event_id: str | None = None
    tracking_number: str
    carrier_code: str | None = None
    event_time: str | None = None
    status_code: str | None = None
    status_text: str | None = None
    location: str | None = None
    description: str | None = None


class CainiaoLikeTrackingResponse(BaseModel):
    tracking_number: str
    carrier_code: str | None = None
    events: list[CainiaoLikeTrackingEvent] = []
    success: bool = True
    error_message: str | None = None
