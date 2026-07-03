from typing import Optional
from pydantic import BaseModel, Field

class MarketplaceSupplierCandidate(BaseModel):
    candidate_id: str
    platform: str
    platform_supplier_id: Optional[str] = None
    supplier_name: str
    product_title: Optional[str] = None
    product_url: Optional[str] = None
    storefront_url: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    moq: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    years_on_platform: Optional[int] = None
    verification_badges: list[str] = Field(default_factory=list)
    transaction_signals: dict = Field(default_factory=dict)
    rating_signals: dict = Field(default_factory=dict)
    delivery_signals: dict = Field(default_factory=dict)
    contact_channels: dict = Field(default_factory=dict)
    openclaw_peer_id: Optional[str] = None
    wangwang_id: Optional[str] = None
    source: str = "unknown"
    source_url: Optional[str] = None
    confidence_score: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)

class SearchResult(BaseModel):
    query: str
    platform: str
    candidates: list[MarketplaceSupplierCandidate] = Field(default_factory=list)
    total_found: int = 0
    connector_mode: str = "mock"
    error: Optional[str] = None
