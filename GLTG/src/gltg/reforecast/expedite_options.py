"""Generates expedite levers to recover schedule slippage."""

from __future__ import annotations

from datetime import date

from ..models.enums import CostImpactLevel, RiskImpactLevel


class ExpediteOptionGenerator:
    """Generates actionable expedite options with days saved and cost/risk impact."""

    LEVERS = [
        {
            "name": "Air freight (sea -> air)",
            "days_saved": 18,
            "cost_impact": CostImpactLevel.VERY_HIGH,
            "risk_impact": RiskImpactLevel.LOW,
            "description": "Replace sea freight with air freight for the main shipment.",
            "precondition": "buyer_approves_air_freight",
        },
        {
            "name": "Stock fabric (pre-book from mill inventory)",
            "days_saved": 14,
            "cost_impact": CostImpactLevel.MEDIUM,
            "risk_impact": RiskImpactLevel.MEDIUM,
            "description": "Source fabric from mill in-stock rather than ordering fresh.",
            "precondition": "stock_fabric_available",
        },
        {
            "name": "Overtime production",
            "days_saved": 5,
            "cost_impact": CostImpactLevel.MEDIUM,
            "risk_impact": RiskImpactLevel.LOW,
            "description": "Run factory on extended hours / weekend shifts.",
            "precondition": "factory_agrees_to_overtime",
        },
        {
            "name": "Parallel cutting & sewing",
            "days_saved": 3,
            "cost_impact": CostImpactLevel.LOW,
            "risk_impact": RiskImpactLevel.LOW,
            "description": "Overlap cutting and sewing on first batches.",
            "precondition": None,
        },
        {
            "name": "Expedited trim ordering",
            "days_saved": 7,
            "cost_impact": CostImpactLevel.MEDIUM,
            "risk_impact": RiskImpactLevel.LOW,
            "description": "Order trims by air or use local supplier at premium.",
            "precondition": "local_trim_supplier_available",
        },
        {
            "name": "Sample approval fast-track",
            "days_saved": 4,
            "cost_impact": CostImpactLevel.LOW,
            "risk_impact": RiskImpactLevel.MEDIUM,
            "description": "Use digital/video approval for pre-production sample.",
            "precondition": "buyer_accepts_digital_approval",
        },
    ]

    def generate(
        self,
        days_needed_to_save: int,
        available_budget: str = "ANY",
    ) -> list[dict]:
        """Return ranked list of expedite options.

        Args:
            days_needed_to_save: How many days must be recovered.
            available_budget: Cost constraint -- LOW, MEDIUM, HIGH, VERY_HIGH, ANY.

        Returns:
            List of lever dicts sorted by days_saved descending.
        """
        options = []
        for lever in self.LEVERS:
            if days_needed_to_save <= 0:
                break
            if available_budget != "ANY":
                lever_cost = lever["cost_impact"].value if hasattr(lever["cost_impact"], "value") else str(lever["cost_impact"])
                budget_ranks = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
                max_rank = budget_ranks.index(available_budget) if available_budget in budget_ranks else 3
                lever_rank = budget_ranks.index(lever_cost) if lever_cost in budget_ranks else 3
                if lever_rank > max_rank:
                    continue

            options.append({
                "name": lever["name"],
                "days_saved": lever["days_saved"],
                "cost_impact": lever["cost_impact"],
                "risk_impact": lever["risk_impact"],
                "description": lever["description"],
                "precondition": lever.get("precondition"),
            })

        return sorted(options, key=lambda x: x["days_saved"], reverse=True)
