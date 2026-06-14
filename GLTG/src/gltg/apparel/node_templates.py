"""Standard node templates for an apparel order workflow."""

from __future__ import annotations

from ..models.enums import ApparelNodeType

# Each entry describes a default workflow step.
# required_inputs/outputs are logical resource names (not node_ids).
DEFAULT_APPAREL_WORKFLOW: list[dict] = [
    {
        "node_type": ApparelNodeType.BUYER_REQUIREMENT_CONFIRMATION,
        "required_inputs": [],
        "outputs": ["buyer_requirements"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION,
        "required_inputs": ["buyer_requirements"],
        "outputs": ["tech_pack"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.FABRIC_SELECTION,
        "required_inputs": ["tech_pack"],
        "outputs": ["fabric_spec"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.FABRIC_AVAILABILITY_CONFIRMATION,
        "required_inputs": ["fabric_spec"],
        "outputs": ["fabric_availability"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.FABRIC_ORDERING,
        "required_inputs": ["fabric_availability"],
        "outputs": ["fabric_ordered"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.FABRIC_DYEING_OR_PRINTING,
        "required_inputs": ["fabric_ordered"],
        "outputs": ["fabric_dyed"],
        "is_optional": True,   # only for dyed/printed fabrics
    },
    {
        "node_type": ApparelNodeType.FABRIC_FINISHING,
        "required_inputs": ["fabric_dyed"],
        "outputs": ["fabric_finished"],
        "is_optional": True,
    },
    {
        "node_type": ApparelNodeType.FABRIC_TESTING,
        "required_inputs": ["fabric_finished"],
        "outputs": ["fabric_tested"],
        "is_optional": True,
    },
    {
        "node_type": ApparelNodeType.TRIM_SELECTION,
        "required_inputs": ["tech_pack"],
        "outputs": ["trim_spec"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.TRIM_AVAILABILITY_CONFIRMATION,
        "required_inputs": ["trim_spec"],
        "outputs": ["trim_availability"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.TRIM_ORDERING,
        "required_inputs": ["trim_availability"],
        "outputs": ["trims_ordered"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.PACKAGING_MATERIAL_CONFIRMATION,
        "required_inputs": ["tech_pack"],
        "outputs": ["packaging_ready"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.SAMPLE_MAKING,
        "required_inputs": ["tech_pack", "fabric_spec"],
        "outputs": ["sample_ready"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.SAMPLE_APPROVAL,
        "required_inputs": ["sample_ready"],
        "outputs": ["sample_approved"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.PP_SAMPLE_APPROVAL,
        "required_inputs": ["sample_approved"],
        "outputs": ["pp_approved"],
        "is_optional": True,
    },
    {
        "node_type": ApparelNodeType.PRODUCTION_SLOT_BOOKING,
        "required_inputs": ["sample_approved"],
        "outputs": ["production_slot"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.CUTTING,
        "required_inputs": ["fabric_tested", "production_slot"],
        "outputs": ["cut_panels"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.SEWING,
        "required_inputs": ["cut_panels", "trims_ordered"],
        "outputs": ["sewn_garments"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.WASHING_OR_FINISHING,
        "required_inputs": ["sewn_garments"],
        "outputs": ["finished_garments"],
        "is_optional": True,
    },
    {
        "node_type": ApparelNodeType.INLINE_QC,
        "required_inputs": ["sewn_garments"],
        "outputs": ["inline_qc_passed"],
        "is_optional": True,
    },
    {
        "node_type": ApparelNodeType.FINAL_QC,
        "required_inputs": ["finished_garments"],
        "outputs": ["qc_approved"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.REWORK_IF_NEEDED,
        "required_inputs": ["qc_approved"],
        "outputs": ["rework_done"],
        "is_optional": True,
    },
    {
        "node_type": ApparelNodeType.PACKING,
        "required_inputs": ["qc_approved", "packaging_ready"],
        "outputs": ["packed"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.LOGISTICS_BOOKING,
        "required_inputs": ["sample_approved"],
        "outputs": ["logistics_booked"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.CUSTOMS_OR_EXPORT_DOCS,
        "required_inputs": ["packed"],
        "outputs": ["customs_cleared"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.SHIPMENT,
        "required_inputs": ["customs_cleared", "logistics_booked"],
        "outputs": ["shipped"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.BUYER_RECEIPT,
        "required_inputs": ["shipped"],
        "outputs": ["received"],
        "is_optional": False,
    },
    {
        "node_type": ApparelNodeType.BUYER_SIGN_OFF,
        "required_inputs": ["received"],
        "outputs": ["signed_off"],
        "is_optional": True,
    },
]
