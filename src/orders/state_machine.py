ORDER_STATES = [
    "DRAFT_FROM_APPROVED_QUOTE",
    "PENDING_BUYER_CONFIRMATION",
    "CONFIRMED",
    "IN_PRODUCTION",
    "QC_PENDING",
    "QC_PASSED",
    "QC_FAILED",
    "READY_TO_SHIP",
    "SHIPPED",
    "DELIVERED",
    "BUYER_SIGNED_OFF",
    "CANCELLED",
]

VALID_TRANSITIONS = {
    "DRAFT_FROM_APPROVED_QUOTE": ["PENDING_BUYER_CONFIRMATION", "CANCELLED"],
    "PENDING_BUYER_CONFIRMATION": ["CONFIRMED", "CANCELLED"],
    "CONFIRMED": ["IN_PRODUCTION", "CANCELLED"],
    "IN_PRODUCTION": ["QC_PENDING", "CANCELLED"],
    "QC_PENDING": ["QC_PASSED", "QC_FAILED"],
    "QC_PASSED": ["READY_TO_SHIP"],
    "QC_FAILED": ["IN_PRODUCTION", "CANCELLED"],
    "READY_TO_SHIP": ["SHIPPED"],
    "SHIPPED": ["DELIVERED"],
    "DELIVERED": ["BUYER_SIGNED_OFF"],
    "BUYER_SIGNED_OFF": [],
    "CANCELLED": [],
}


def transition(current: str, target: str) -> str:
    if target not in VALID_TRANSITIONS.get(current, []):
        raise ValueError(f"Invalid order transition: {current} → {target}")
    return target
