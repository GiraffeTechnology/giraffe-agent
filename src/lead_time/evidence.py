"""Evidence tracking utilities for lead time components."""

EVIDENCE_TYPE_SUPPLIER_STATED = "supplier_stated"
EVIDENCE_TYPE_AI_CALCULATED = "ai_calculated"
EVIDENCE_TYPE_HUMAN_CONFIRMED = "human_confirmed"
EVIDENCE_TYPE_DEFAULT_ASSUMPTION = "default_assumption"


def make_evidence_ref(evidence_type: str, source_id: str | None = None, note: str | None = None) -> str:
    parts = [f"type:{evidence_type}"]
    if source_id:
        parts.append(f"src:{source_id}")
    if note:
        parts.append(f"note:{note}")
    return "|".join(parts)


def validate_component_has_evidence(component_id: str, evidence_type: str | None, evidence_ref: str | None) -> list[str]:
    """Returns list of validation warnings for a component."""
    warnings = []
    if not evidence_type:
        warnings.append(f"component {component_id}: missing evidence_type")
    if not evidence_ref:
        warnings.append(f"component {component_id}: missing evidence_ref")
    return warnings
