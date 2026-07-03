"""
M-side supplier profile persistence — JSON file storage under data/supplier_profiles/.
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.core_schema.m_side_types import MSideSupplierProfile, SupplierCapability

_DATA_DIR = Path("data/supplier_profiles")


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _profile_path(supplier_id: str) -> Path:
    return _DATA_DIR / f"{supplier_id}.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_supplier_profile(
    supplier_id: str | None = None,
    name: str = "",
    channel: str | None = None,
    external_user_id: str | None = None,
    contact_name: str | None = None,
    phone_or_handle: str | None = None,
    language_preference: str = "zh",
    region: str | None = None,
    capability: SupplierCapability | None = None,
) -> MSideSupplierProfile:
    """Create and persist a new supplier profile."""
    _ensure_dir()
    sid = supplier_id or f"sup_{uuid.uuid4().hex[:10]}"
    now = _utcnow()
    profile = MSideSupplierProfile(
        supplier_id=sid,
        supplier_name=name,
        contact_name=contact_name,
        channel=channel,
        external_user_id=external_user_id,
        phone_or_handle=phone_or_handle,
        language_preference=language_preference,
        region=region,
        capability=capability or SupplierCapability(),
        created_at=now,
        updated_at=now,
    )
    return save_supplier_profile(profile)


def get_supplier_profile(supplier_id: str) -> MSideSupplierProfile | None:
    """Load supplier profile by ID. Returns None if not found."""
    _ensure_dir()
    path = _profile_path(supplier_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MSideSupplierProfile.model_validate(data)


def save_supplier_profile(profile: MSideSupplierProfile) -> MSideSupplierProfile:
    """Persist supplier profile."""
    _ensure_dir()
    profile.updated_at = _utcnow()
    path = _profile_path(profile.supplier_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return profile


def list_supplier_profiles() -> list[MSideSupplierProfile]:
    """List all persisted supplier profiles."""
    _ensure_dir()
    profiles = []
    for path in sorted(_DATA_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            profiles.append(MSideSupplierProfile.model_validate(data))
        except Exception:
            pass
    return profiles
