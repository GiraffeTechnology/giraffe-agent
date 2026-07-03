from pydantic import BaseModel, Field
from typing import Any, Optional

class MissingField(BaseModel):
    field_name: str
    description: str
    question: str

class BuyerRequirement(BaseModel):
    project_id: str = ""
    raw_text: str = ""
    category: str = ""
    product_type: str = ""
    quantity: Optional[int] = None
    quantity_unit: str = "pcs"
    fabric_material: str = ""
    gsm: Optional[int] = None
    color: str = ""
    size_ratio: str = ""
    packaging: str = ""
    destination: str = ""
    target_unit_price: Optional[float] = None
    target_currency: str = "USD"
    delivery_deadline_iso: Optional[str] = None
    delivery_days: Optional[int] = None
    incoterms: str = ""
    logistics_preference: str = ""
    material_spec: str = ""
    tolerance: str = ""
    surface_finish: str = ""
    cad_attachment: bool = False
    process_type: str = ""
    notes: str = ""
    missing_fields: list[MissingField] = Field(default_factory=list)
    confidence: float = 0.0
    language: str = "en"
    extra: dict[str, Any] = Field(default_factory=dict)

    def is_complete(self) -> bool:
        return len(self.missing_fields) == 0 and self.quantity is not None and bool(self.product_type)
