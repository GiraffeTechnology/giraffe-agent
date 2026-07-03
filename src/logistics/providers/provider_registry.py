"""
Provider registry — selects the logistics provider based on config.
LOGISTICS_PROVIDER=mock → MockProvider
LOGISTICS_PROVIDER=cainiao_like → CainiaoLikeProvider
"""
from __future__ import annotations
from src.logistics.providers.base_provider import LogisticsProviderBase
from src.logistics.providers.provider_config import get_provider_name, is_production_mode
from src.m_side.m_event_logger import log_m_event


def get_logistics_provider(provider_name: str | None = None) -> LogisticsProviderBase:
    name = provider_name or get_provider_name()
    log_m_event(
        event_type="LOGISTICS_PROVIDER_SELECTED",
        payload={"provider": name},
    )
    if name == "cainiao_like":
        from src.logistics.providers.cainiao_like_provider import CainiaoLikeProvider
        return CainiaoLikeProvider()
    if name == "mock":
        from src.logistics.providers.mock_provider import MockProvider
        return MockProvider()
    if is_production_mode():
        raise ValueError(f"Unknown logistics provider '{name}' in production mode. Set LOGISTICS_PROVIDER.")
    from src.logistics.providers.mock_provider import MockProvider
    return MockProvider()
