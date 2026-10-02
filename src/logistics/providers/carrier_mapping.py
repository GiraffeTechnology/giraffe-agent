# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""Carrier name → carrier code mapping (configurable, not exhaustive)."""

from __future__ import annotations
CARRIER_NAME_TO_CODE: dict[str, str] = {
    '\u987a\u4e30': "SF",
    "sf express": "SF",
    "sf": "SF",
    '\u4e2d\u901a': "ZTO",
    "zto": "ZTO",
    '\u5706\u901a': "YTO",
    "yto": "YTO",
    '\u7533\u901a': "STO",
    "sto": "STO",
    '\u97f5\u8fbe': "YD",
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
