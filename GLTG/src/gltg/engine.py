"""LeadTimeGraphEngine — the main evaluation orchestrator."""

from __future__ import annotations

import logging
from datetime import date

from .models.graph import LeadTimeGraph
from .models.order import ApparelOrderInput
from .models.packet import DeliveryFeasibilityPacket
from .models.path import DeliveryPathOption
from .models.reforecast import ProgressEvent

from .apparel.order_mapper import ApparelOrderMapper
from .apparel.validators import ApparelOrderValidator
from .estimation.duration_estimator import DurationEstimator
from .estimation.on_time_probability import OnTimeProbabilityCalculator
from .graph.builder import GraphBuilder
from .graph.dependency_resolver import DependencyResolver
from .graph.critical_path import CriticalPathFinder
from .enumeration.path_enumerator import PathEnumerator
from .enumeration.path_pruner import PathPruner
from .enumeration.batch_split import BatchSplitAnalyzer
from .enumeration.alternative_routes import AlternativeRouteGenerator
from .enumeration.option_ranker import OptionRanker
from .packets.feasibility_packet import FeasibilityPacketBuilder
from .reforecast.reforecast_engine import ReforecastEngine

logger = logging.getLogger(__name__)


class LeadTimeGraphEngine:
    """Orchestrates the full GLTG evaluation pipeline."""

    def __init__(self) -> None:
        self._validator = ApparelOrderValidator()
        self._mapper = ApparelOrderMapper()
        self._duration_estimator = DurationEstimator()
        self._builder = GraphBuilder()
        self._resolver = DependencyResolver()
        self._cp_finder = CriticalPathFinder()
        self._enumerator = PathEnumerator()
        self._pruner = PathPruner()
        self._splitter = BatchSplitAnalyzer()
        self._alt_routes = AlternativeRouteGenerator()
        self._ranker = OptionRanker()
        self._packet_builder = FeasibilityPacketBuilder()
        self._reforecast_engine = ReforecastEngine()
        self._otp_calc = OnTimeProbabilityCalculator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_graph(self, order_input: ApparelOrderInput) -> LeadTimeGraph:
        """Build and resolve the lead-time graph for an order."""
        nodes = self._mapper.map(order_input)

        # Refine duration estimates with available evidence
        for node in nodes:
            # Find supplier response for this node type
            sr = next(
                (r for r in order_input.supplier_responses if r.node_type == node.node_type),
                None,
            )
            participant = None
            if node.participant_id:
                participant = next(
                    (p for p in order_input.participants if p.participant_id == node.participant_id),
                    None,
                )
            node.duration_estimate = self._duration_estimator.estimate(
                node_type=node.node_type,
                participant=participant,
                supplier_response=sr,
                memory_records=order_input.supplier_memory,
                progress_events=[
                    e for e in order_input.progress_events if e.node_id == node.node_id
                ],
                quantity=order_input.quantity,
                calendar=order_input.calendar,
            )

        graph = self._builder.build(order_input, nodes)
        start = date.today()
        self._resolver.resolve(graph, start, order_input.calendar)
        critical = self._cp_finder.find(graph)
        bottlenecks = self._cp_finder.find_bottlenecks(graph, critical)

        graph.metadata["critical_path"] = critical
        graph.metadata["bottleneck_nodes"] = bottlenecks

        return graph

    def enumerate_options(self, graph: LeadTimeGraph) -> list[DeliveryPathOption]:
        """Generate all delivery path options from a resolved graph."""
        return self._enumerator.enumerate(graph)

    def evaluate(self, order_input: ApparelOrderInput) -> DeliveryFeasibilityPacket:
        """Full evaluation pipeline.

        Steps:
        1. Validate order input
        2. Build and resolve graph (with duration estimation)
        3. Find critical path
        4. Enumerate options
        5. Prune infeasible options
        6. Generate batch-split and alternative-route options
        7. Compute on-time probabilities
        8. Rank options (top 3)
        9. Apply feasibility rules (0/1/2/3+ options)
        10. Build and return DeliveryFeasibilityPacket
        """
        logger.debug("Evaluating order %s", order_input.order_id)

        # Step 1: Validate
        missing_fields, validation_flags = self._validator.validate(order_input)

        # Step 2-3: Build, resolve, critical path
        graph = self.build_graph(order_input)
        critical_path: list[str] = graph.metadata.get("critical_path", [])
        bottlenecks: list[str] = graph.metadata.get("bottleneck_nodes", [])

        # Step 4: Enumerate base options
        base_options = self.enumerate_options(graph)

        # Step 5: Prune infeasible
        classified = self._pruner.prune(base_options, order_input.requested_delivery_date)

        # Step 6: Generate variants
        all_options: list[DeliveryPathOption] = list(classified)

        feasible_base = self._pruner.filter_feasible(classified)
        if feasible_base:
            best = feasible_base[0]
            # Batch split variants
            splits = self._splitter.generate_splits(best, order_input.quantity)
            classified_splits = self._pruner.prune(splits, order_input.requested_delivery_date)
            all_options.extend(classified_splits)

            # Alternative routes
            alts = self._alt_routes.generate(best, order_input.requested_delivery_date)
            classified_alts = self._pruner.prune(alts, order_input.requested_delivery_date)
            all_options.extend(classified_alts)

        # Step 7: Compute on-time probabilities
        for option in all_options:
            if option.on_time_probability is None:
                otp = self._otp_calc.from_option_dates(
                    commitable_date=option.commitable_date,
                    risk_adjusted_date=option.risk_adjusted_latest_date,
                    target_date=order_input.requested_delivery_date,
                )
                option.on_time_probability = otp

        # Step 8: Rank (top 3, capped by distinct participant count)
        unique_participant_count = len(order_input.participants)
        max_options = min(3, unique_participant_count) if unique_participant_count > 0 else 0
        ranked = self._ranker.rank(all_options, order_input.requested_delivery_date)
        ranked = ranked[:max_options]

        # Propagate missing fields to options
        for opt in ranked:
            opt.missing_fields = list(missing_fields)

        # Collect risk flags from all ranked options
        all_risk_flags = list(validation_flags)
        seen_codes = {rf.code for rf in all_risk_flags}
        for opt in ranked:
            for rf in opt.risk_flags:
                if rf.code not in seen_codes:
                    all_risk_flags.append(rf)
                    seen_codes.add(rf.code)

        # Step 9-10: Build packet (applies 0/1/2/3+ rules internally)
        packet = self._packet_builder.build(
            order_id=order_input.order_id,
            options=ranked,
            missing_fields=missing_fields,
            risk_flags=all_risk_flags,
            requested_date=order_input.requested_delivery_date,
        )

        # Back-fill critical path / bottleneck from graph if packet doesn't have them
        if not packet.critical_path:
            packet.critical_path = critical_path
        if not packet.bottleneck_nodes:
            packet.bottleneck_nodes = bottlenecks

        logger.debug(
            "Evaluation complete for %s: status=%s, options=%d",
            order_input.order_id,
            packet.status,
            len(packet.options),
        )
        return packet

    def reforecast(
        self,
        existing_packet: DeliveryFeasibilityPacket,
        events: list[ProgressEvent],
    ) -> DeliveryFeasibilityPacket:
        """Re-evaluate an existing packet given new progress events."""
        return self._reforecast_engine.reforecast(existing_packet, events)
