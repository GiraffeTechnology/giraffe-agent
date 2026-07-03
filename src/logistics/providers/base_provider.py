"""Abstract base class for logistics providers."""
from __future__ import annotations
from abc import ABC, abstractmethod


class LogisticsProviderBase(ABC):
    provider_name: str = "base"

    @abstractmethod
    def create_or_bind_shipment(
        self,
        carrier_code: str | None,
        tracking_number: str,
        metadata: dict | None = None,
    ) -> dict:
        ...

    @abstractmethod
    def fetch_tracking_events(
        self,
        carrier_code: str | None,
        tracking_number: str,
    ) -> list[dict]:
        ...

    @abstractmethod
    def parse_webhook_payload(
        self,
        payload: dict,
        headers: dict | None = None,
    ) -> list[dict]:
        ...

    def verify_webhook_signature(
        self,
        payload: bytes,
        headers: dict,
    ) -> bool:
        return False

    @abstractmethod
    def normalize_event(self, raw_event: dict) -> dict:
        ...
