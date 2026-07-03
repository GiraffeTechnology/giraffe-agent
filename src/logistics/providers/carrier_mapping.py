"""Carrier name → carrier code mapping (configurable, not exhaustive)."""

from __future__ import annotations
CARRIER_NAME_TO_CODE: dict[str, str] = {
    "顺丰": "SF",
    "sf express": "SF",
    "sf": "SF",
    "中通": "ZTO",
    "zto": "ZTO",
    "圆通": "YTO",
    "yto": "YTO",
    "申通": "STO",
    "sto": "STO",
    "韵达": "YD",
    "yd": "YD",
    "ems": "EMS",
    "dhl": "DHL",
    "fedex": "FEDEX",
    "ups": "UPS",
    "tnt": "TNT",
    "cainiao": "CAINIAO",
}


def normalize_carrier_name(raw_name: str) -> tuple[str | None, str | None]:
    """Return (carrier_name, carrier_code) from a raw carrier string."""
    key = raw_name.strip().lower()
    code = CARRIER_NAME_TO_CODE.get(key)
    if code:
        return raw_name.strip(), code
    for k, v in CARRIER_NAME_TO_CODE.items():
        if k in key or key in k:
            return raw_name.strip(), v
    return raw_name.strip() if raw_name else None, None
