"""Resolves earliest/latest dates for each node in topological order."""

from __future__ import annotations

import math
from datetime import date

from ..models.graph import LeadTimeGraph
from ..models.node import LeadTimeNode
from ..models.reforecast import CalendarConfig
from .calendars import CalendarCalculator
from .topological import topological_sort


class DependencyResolver:
    """Forward-pass scheduler: computes dates for all nodes."""

    def __init__(self) -> None:
        self._cal = CalendarCalculator()

    def resolve(
        self,
        graph: LeadTimeGraph,
        start_date: date,
        calendar: CalendarConfig | None,
    ) -> LeadTimeGraph:
        """Compute date fields on each node in-place and return the graph.

        Uses a forward pass in topological order.
        For each node:
          earliest_start = max(predecessor earliest_finish + lag) or start_date
          earliest_finish = earliest_start + p50
          most_likely_finish = earliest_start + p80
          commitable_finish = earliest_start + p90
          risk_adjusted_finish = earliest_start + max (or p90 * 1.2)
        """
        ordered = topological_sort(graph.nodes, graph.edges)

        # Map: node_id -> earliest_finish (date) for propagation
        ef_map: dict[str, date] = {}

        for node in ordered:
            # Find latest predecessor finish date
            incoming = graph.get_edges_to(node.node_id)
            pred_dates: list[date] = []
            for edge in incoming:
                pred_ef = ef_map.get(edge.from_node_id)
                if pred_ef is not None:
                    lag_date = self._cal.add_working_days(pred_ef, edge.lag_days, calendar)
                    pred_dates.append(lag_date)

            earliest_start = max(pred_dates) if pred_dates else start_date
            earliest_start = self._cal.ensure_working_day(earliest_start, calendar)

            # Duration estimates
            dur = node.duration_estimate
            if dur is None:
                p50 = p80 = p90 = 2.0
                max_d = 7.0
            else:
                p50 = max(dur.p50_days, 0.5)
                p80 = max(dur.p80_days, p50)
                p90 = max(dur.p90_days, p80)
                max_d = dur.max_days if dur.max_days else p90 * 1.2

            earliest_finish = self._cal.add_working_days(earliest_start, p50, calendar)
            most_likely_finish = self._cal.add_working_days(earliest_start, p80, calendar)
            commitable_finish = self._cal.add_working_days(earliest_start, p90, calendar)
            risk_adj_days = max(max_d, math.ceil(p90 * 1.15))
            risk_adjusted_finish = self._cal.add_working_days(earliest_start, risk_adj_days, calendar)

            # Update node (models are mutable via __dict__ assignment)
            node.earliest_start = earliest_start
            node.earliest_finish = earliest_finish
            node.most_likely_finish = most_likely_finish
            node.commitable_finish = commitable_finish
            node.risk_adjusted_finish = risk_adjusted_finish

            ef_map[node.node_id] = earliest_finish

        # Replace nodes list with resolved nodes (same objects, already mutated)
        return graph
