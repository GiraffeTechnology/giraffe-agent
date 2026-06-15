"""Resolves earliest/latest dates for each node in topological order."""

from __future__ import annotations

import math
from datetime import date

from ..models.graph import LeadTimeGraph
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
        node_finish_floors: dict[str, date] | None = None,
    ) -> LeadTimeGraph:
        """Compute date fields on each node in-place and return the graph.

        Uses a forward pass in topological order, tracking three separate
        propagation maps so that each percentile (p50/p80/p90) is propagated
        independently through the chain.

          earliest_start    = max(predecessor p50_finish + lag) or start_date
          most_likely_start = max(predecessor p80_finish + lag) or start_date
          commitable_start  = max(predecessor p90_finish + lag) or start_date

          earliest_finish    = earliest_start    + p50
          most_likely_finish = most_likely_start + p80
          commitable_finish  = commitable_start  + p90
          risk_adjusted_finish = commitable_start + max(max_days, ceil(p90*1.15))

        node_finish_floors: optional dict of node_id -> minimum commitable_finish.
          Used by reforecast to anchor event-applied dates so re-resolve does not
          discard them.
        """
        ordered = topological_sort(graph.nodes, graph.edges)

        # Separate propagation maps for each percentile
        ef_map: dict[str, date] = {}   # p50 earliest_finish
        mlf_map: dict[str, date] = {}  # p80 most_likely_finish
        cf_map: dict[str, date] = {}   # p90 commitable_finish

        # Seed maps from floors (already-applied event dates)
        if node_finish_floors:
            for nid, floor_date in node_finish_floors.items():
                ef_map[nid] = floor_date
                mlf_map[nid] = floor_date
                cf_map[nid] = floor_date

        for node in ordered:
            # Nodes that are anchored (event-applied): skip recompute, just
            # propagate their anchored finish into downstream maps.
            if node_finish_floors and node.node_id in node_finish_floors:
                # Already seeded in maps above; keep existing node dates.
                continue

            incoming = graph.get_edges_to(node.node_id)

            ef_starts: list[date] = []
            mlf_starts: list[date] = []
            cf_starts: list[date] = []

            for edge in incoming:
                pred_ef = ef_map.get(edge.from_node_id)
                pred_mlf = mlf_map.get(edge.from_node_id)
                pred_cf = cf_map.get(edge.from_node_id)
                lag = edge.lag_days

                if pred_ef is not None:
                    ef_starts.append(self._cal.add_working_days(pred_ef, lag, calendar))
                if pred_mlf is not None:
                    mlf_starts.append(self._cal.add_working_days(pred_mlf, lag, calendar))
                if pred_cf is not None:
                    cf_starts.append(self._cal.add_working_days(pred_cf, lag, calendar))

            earliest_start = max(ef_starts) if ef_starts else start_date
            most_likely_start = max(mlf_starts) if mlf_starts else start_date
            commitable_start = max(cf_starts) if cf_starts else start_date

            earliest_start = self._cal.ensure_working_day(earliest_start, calendar)
            most_likely_start = self._cal.ensure_working_day(most_likely_start, calendar)
            commitable_start = self._cal.ensure_working_day(commitable_start, calendar)

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
            most_likely_finish = self._cal.add_working_days(most_likely_start, p80, calendar)
            commitable_finish = self._cal.add_working_days(commitable_start, p90, calendar)
            risk_adj_days = max(max_d, math.ceil(p90 * 1.15))
            risk_adjusted_finish = self._cal.add_working_days(commitable_start, risk_adj_days, calendar)

            node.earliest_start = earliest_start
            node.earliest_finish = earliest_finish
            node.most_likely_finish = most_likely_finish
            node.commitable_finish = commitable_finish
            node.risk_adjusted_finish = risk_adjusted_finish

            ef_map[node.node_id] = earliest_finish
            mlf_map[node.node_id] = most_likely_finish
            cf_map[node.node_id] = commitable_finish

        return graph
