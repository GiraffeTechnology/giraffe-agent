RFQ_STATES = [
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED_TO_SEND",
    "SENT",
    "RECEIVED",
    "PARTIAL_RESPONSE",
    "COMPLETE_RESPONSE",
    "EXPIRED",
    "CANCELLED",
]

VALID_TRANSITIONS = {
    "DRAFT": ["PENDING_APPROVAL", "CANCELLED"],
    "PENDING_APPROVAL": ["APPROVED_TO_SEND", "DRAFT", "CANCELLED"],
    "APPROVED_TO_SEND": ["SENT", "CANCELLED"],
    "SENT": ["RECEIVED", "PARTIAL_RESPONSE", "EXPIRED", "CANCELLED"],
    "RECEIVED": ["PARTIAL_RESPONSE", "COMPLETE_RESPONSE"],
    "PARTIAL_RESPONSE": ["COMPLETE_RESPONSE", "EXPIRED"],
    "COMPLETE_RESPONSE": [],
    "EXPIRED": [],
    "CANCELLED": [],
}


def transition(current: str, target: str) -> str:
    if target not in VALID_TRANSITIONS.get(current, []):
        raise ValueError(f"Invalid RFQ transition: {current} → {target}")
    return target
