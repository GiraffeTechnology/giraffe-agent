# GLTG -- Giraffe Lead-Time Graph

**Version 1.0.0**

GLTG is an evidence-weighted execution-time graph model for apparel and textile orders. It is not a simple lead-time calculator.

GLTG converts dynamic order forms, participant capabilities, supplier confirmations, production progress, QC events, logistics states, and supplier memory into risk-adjusted delivery plans, commitable dates, critical paths, acceleration signals, and delivery feasibility packets.

---

## Why GLTG Is Not a Simple Lead-Time Calculator

A simple calculator applies `max(materials, trims) + production + QC + shipping`. GLTG does not.

GLTG:

- Builds a real dependency graph of apparel workflow nodes
- Resolves node schedules using topological ordering with calendar constraints
- Weights duration estimates by evidence quality (actual progress > supplier confirmation > historical memory > supplier quote > category baseline > AI estimate)
- Enumerates feasible delivery path options across different participant combinations
- Prunes infeasible paths with explanatory traces
- Detects the critical path and bottleneck nodes
- Computes on-time probability using p50/p80/p90 estimates
- Generates batch and split delivery options
- Reforecasts after progress events
- Generates expedite options to recover delayed orders
- Returns 0 to 3 ranked delivery options -- never crashes with fewer than 3 suppliers

---

## Installation

Requires Python 3.11+.

```bash
cd GLTG
uv sync
# or
pip install -e ".[dev]"
```

---

## Quick Start

```python
from gltg import LeadTimeGraphEngine, ApparelOrderInput

engine = LeadTimeGraphEngine()

order = ApparelOrderInput(
    order_id="ORD-001",
    product_type="men_shirt_cotton",
    quantity=10000,
    requested_delivery_date=None,
    dynamic_form={"fabric_type": "cotton", "wash_required": True},
    participants=[],
)

packet = engine.evaluate(order)

print(packet.status)
print(packet.commitable_date)
print(packet.critical_path)
print(packet.risk_flags)
```

---

## Python API

```python
from gltg import (
    LeadTimeGraphEngine,
    ApparelOrderInput,
    ParticipantProfile,
    SupplierMemoryRecord,
    ProgressEvent,
    DeliveryFeasibilityPacket,
    DecisionPacket,
    LeadTimeGraph,
    LeadTimeNode,
    LeadTimeEdge,
    RiskFlag,
)

engine = LeadTimeGraphEngine()

# Build a graph
graph = engine.build_graph(order_input)

# Enumerate options
options = engine.enumerate_options(graph)

# Full evaluation
packet = engine.evaluate(order_input)

# Reforecast after events
updated_packet = engine.reforecast(packet, events)
```

### `DeliveryFeasibilityPacket` fields

| Field | Type | Description |
|---|---|---|
| `status` | `FeasibilityStatus` | FEASIBLE / LIMITED_OPTIONS / NO_FEASIBLE_OPTION / REQUIRES_EXPEDITE |
| `options` | `list[DeliveryPathOption]` | 0 to 3 ranked options |
| `commitable_date` | `date \| None` | P90 commitable delivery date |
| `most_likely_date` | `date \| None` | P80 most likely delivery date |
| `earliest_feasible_date` | `date \| None` | P50 earliest feasible date |
| `on_time_probability` | `float \| None` | Probability of on-time delivery |
| `critical_path` | `list[str]` | Ordered list of critical node IDs |
| `bottleneck_nodes` | `list[str]` | Nodes causing most delay |
| `risk_flags` | `list[RiskFlag]` | Risk signals detected |
| `missing_fields` | `list[str]` | Fields missing from order input |
| `evidence_summary` | `list[EvidenceItem]` | Evidence used in computation |
| `recommended_action` | `str \| None` | Suggested next action |
| `human_review_required` | `bool` | Always True in v1.0 |

---

## CLI Usage

```bash
# Evaluate an order
gltg evaluate examples/10000_shirts_order.json

# Evaluate with human-readable summary
gltg evaluate examples/10000_shirts_order.json --summary

# Write output to file
gltg evaluate examples/10000_shirts_order.json --output result.json

# Reforecast after progress events
gltg reforecast examples/10000_shirts_order.json examples/10000_shirts_progress_events.json --summary

# Zero supplier case
gltg evaluate examples/zero_suppliers.json --summary

# One supplier case
gltg evaluate examples/one_supplier.json --summary

# Two supplier case
gltg evaluate examples/two_suppliers.json --summary
```

---

## Examples

| File | Description |
|---|---|
| `examples/10000_shirts_order.json` | 10,000 men's cotton shirts, FOB Shenzhen, 45-day requirement |
| `examples/zero_suppliers.json` | Valid order with no participants -- returns NO_FEASIBLE_OPTION |
| `examples/one_supplier.json` | Single supplier -- returns LIMITED_OPTIONS + LIMITED_COMPETITION |
| `examples/two_suppliers.json` | Two suppliers -- returns LIMITED_OPTIONS + LIMITED_COMPARISON |

---

## Test Commands

```bash
cd GLTG

# Run all tests
uv run pytest

# Run acceptance scripts
uv run python scripts/run_10000_shirts_acceptance.py
uv run python scripts/run_zero_one_two_supplier_cases.py
uv run python scripts/verify_gltg_5x.py
```

---

## Integration with Giraffe Agent

```python
from gltg.integrations.giraffe_agent_adapter import GiraffeAgentAdapter

adapter = GiraffeAgentAdapter()

# Convert agent dynamic form to GLTG input
order_input = adapter.dynamic_form_to_order(agent_form_data)

# Evaluate
from gltg import LeadTimeGraphEngine
engine = LeadTimeGraphEngine()
packet = engine.evaluate(order_input)

# Convert back to agent response shape
agent_response = adapter.packet_to_agent_response(packet)
```

---

## Fewer-Than-3 Rule

| Candidate count | Status | Risk flags |
|---|---|---|
| 0 | `NO_FEASIBLE_OPTION` | -- |
| 1 | `LIMITED_OPTIONS` | `LIMITED_COMPETITION` |
| 2 | `LIMITED_OPTIONS` | `LIMITED_COMPARISON` |
| ?3 | `FEASIBLE` | -- |

GLTG never crashes or invents suppliers to fill 3 slots.

---

## Supplier Lead Times Are Evidence, Not Truth

Supplier-stated dates are one evidence source among many. GLTG also considers:

- Participant capability and capacity
- Historical supplier memory (past actual vs. stated)
- Apparel category baseline lead times
- Actual production progress events
- Calendar constraints (working days, holidays)
- Missing evidence (creates risk flags and lowers confidence)

---

## Documentation

| Doc | Description |
|---|---|
| `docs/model_spec.md` | Full model specification |
| `docs/evidence_weighting.md` | Evidence hierarchy and weighting |
| `docs/apparel_node_templates.md` | All 28 apparel node types |
| `docs/path_enumeration.md` | Path enumeration algorithm |
| `docs/reforecasting.md` | Reforecast after progress events |
| `docs/integration_guide.md` | Integrating with Giraffe Agent |
| `docs/api_reference.md` | Full API reference |
| `docs/acceptance_criteria.md` | Acceptance criteria for v1.0 |
| `docs/glossary.md` | Terminology glossary |

---

## Limitations (v1.0)

1. Calendar support uses simple working-day arithmetic. Complex multi-region holiday calendars are not yet supported.
2. On-time probability uses a normal distribution approximation over p50/p80/p90 quantiles. A full Monte Carlo simulation is planned for v2.0.
3. Path enumeration generates options from participant combinations but does not yet support full mixed-factory graph branching.
4. All outputs carry `human_review_required=True`. Automated commitments require human sign-off.

---

## Next Iteration

1. Monte Carlo simulation for delivery probability distributions
2. Multi-region calendar support with supplier timezone-aware scheduling
3. Full mixed-factory graph branching with cost modeling
4. Live webhook integration for real-time reforecast triggers
5. Buyer portal output adapter

---

## License

See `LICENSE` file.

---

## Version

GLTG 1.0.0
