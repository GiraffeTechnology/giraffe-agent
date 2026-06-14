"""Workflow template selection — adapts the default workflow to order specifics."""

from __future__ import annotations

from ..models.order import ApparelOrderInput
from ..models.enums import ApparelNodeType
from .node_templates import DEFAULT_APPAREL_WORKFLOW


class ApparelWorkflowTemplate:
    """Selects and customises the set of nodes for a given order."""

    def get_nodes_for_order(self, order: ApparelOrderInput) -> list[dict]:
        """Return an ordered list of node spec dicts for this order.

        Optionality rules:
        - FABRIC_DYEING_OR_PRINTING / FABRIC_FINISHING: include when
          dynamic_form has 'requires_dyeing' or 'requires_printing' truthy.
        - FABRIC_TESTING: include when 'requires_fabric_testing' truthy.
        - PP_SAMPLE_APPROVAL: include when 'requires_pp_sample' truthy.
        - WASHING_OR_FINISHING: include when 'requires_washing' truthy.
        - INLINE_QC: include when 'requires_inline_qc' truthy.
        - REWORK_IF_NEEDED: always included (risk buffer).
        - BUYER_SIGN_OFF: include when 'requires_sign_off' truthy.
        """
        form = order.dynamic_form or {}
        optional_flags: dict[ApparelNodeType, bool] = {
            ApparelNodeType.FABRIC_DYEING_OR_PRINTING: bool(
                form.get("requires_dyeing") or form.get("requires_printing")
            ),
            ApparelNodeType.FABRIC_FINISHING: bool(
                form.get("requires_dyeing") or form.get("requires_printing")
                or form.get("requires_finishing")
            ),
            ApparelNodeType.FABRIC_TESTING: bool(form.get("requires_fabric_testing", True)),
            ApparelNodeType.PP_SAMPLE_APPROVAL: bool(form.get("requires_pp_sample", False)),
            ApparelNodeType.WASHING_OR_FINISHING: bool(form.get("requires_washing", False)),
            ApparelNodeType.INLINE_QC: bool(form.get("requires_inline_qc", False)),
            ApparelNodeType.REWORK_IF_NEEDED: True,  # always include as risk buffer
            ApparelNodeType.BUYER_SIGN_OFF: bool(form.get("requires_sign_off", False)),
        }

        selected: list[dict] = []
        for spec in DEFAULT_APPAREL_WORKFLOW:
            nt = spec["node_type"]
            if not spec.get("is_optional", False):
                selected.append(dict(spec))
            elif optional_flags.get(nt, False):
                selected.append(dict(spec))

        return selected
