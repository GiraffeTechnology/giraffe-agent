# GLTG Integration Guide

## Overview

This guide explains how to install GLTG inside the Giraffe Agent repository, import it in agent code, and use the main integration points: `GiraffeAgentAdapter`, `load_order_from_json`, and the packet serializers.

---

## Installation

GLTG is distributed as an editable local package. From the repository root:

```bash
cd GLTG
uv pip install -e .
```

Or using pip:

```bash
pip install -e GLTG/
```

For development with test dependencies:

```bash
uv pip install -e "GLTG/[dev]"
```

Once installed, the `gltg` package is importable from any Python environment within the project. The CLI command `gltg` is also available.

### sys.path Alternative (for scripts)

If you do not want to install the package, add `src/` to `sys.path` at the top of your script:

```python
import sys, pathlib
ROOT = pathlib.Path(__file__).parent.parent  # adjust to reach GLTG/
sys.path.insert(0, str(ROOT / "src"))
import gltg
```

---

## Using GiraffeAgentAdapter

The `GiraffeAgentAdapter` bridges the Giraffe Agent's dynamic form payloads and the GLTG data models.

### Import

```python
from gltg.integrations.giraffe_agent_adapter import GiraffeAgentAdapter
```

### dynamic_form_to_order

Converts a raw agent form payload dict into an `ApparelOrderInput`:

```python
adapter = GiraffeAgentAdapter()

form_data = {
    "order_id": "ORD-2025-999",
    "product_type": "woven_shirt",
    "quantity": 3000,
    "requested_delivery_date": "2025-10-01",
    "trade_term": "FOB",
    "destination": "Hamburg, Germany",
    "dynamic_form": {
        "fabric_type": "100% cotton",
        "color": "navy",
        "quality_standard": "AQL 2.5",
    },
    "participants": [
        {
            "participant_id": "FACT-999",
            "name": "My Factory",
            "participant_type": "GARMENT_FACTORY",
            "capabilities": [
                {"capability_id": "c1", "node_type": "CUTTING", "capacity_per_day": 600},
                {"capability_id": "c2", "node_type": "SEWING", "capacity_per_day": 500},
                {"capability_id": "c3", "node_type": "PACKING", "capacity_per_day": 1000},
            ],
        }
    ],
}

order = adapter.dynamic_form_to_order(form_data)
```

### packet_to_agent_response

Converts a `DeliveryFeasibilityPacket` back to the agent's simplified output format:

```python
from gltg.engine import LeadTimeGraphEngine

engine = LeadTimeGraphEngine()
packet = engine.evaluate(order)

response = adapter.packet_to_agent_response(packet)
# response is a plain dict suitable for JSON serialization
print(response["status"])            # e.g. "FEASIBLE"
print(response["commitable_date"])   # e.g. "2025-09-28"
print(response["top_risks"])         # list of risk flag codes
print(response["options"])           # list of option summaries
```

---

## Importing and Using GLTG from Agent Code

### Full Evaluation Pipeline

```python
from gltg.engine import LeadTimeGraphEngine
from gltg.models.order import ApparelOrderInput

order = ApparelOrderInput(
    order_id="ORD-AGENT-001",
    product_type="woven_shirt",
    quantity=5000,
    requested_delivery_date=date(2025, 10, 15),
    participants=[...],  # list[ParticipantProfile]
    supplier_memory=[...],  # list[SupplierMemoryRecord]
)

engine = LeadTimeGraphEngine()
packet = engine.evaluate(order)

print(packet.status.value)
print(packet.commitable_date)
print(len(packet.options))
```

### Loading from JSON

```python
from gltg.integrations.json_io import load_order_from_json, load_events_from_json

order = load_order_from_json("path/to/order.json")
events = load_events_from_json("path/to/events.json")
```

### Reforecasting

```python
updated_packet = engine.reforecast(packet, events)

print(f"Before: {packet.commitable_date}")
print(f"After:  {updated_packet.commitable_date}")
```

---

## Serializing and Deserializing Packets

The `serializers` module provides round-trip JSON support for `DeliveryFeasibilityPacket`:

```python
from gltg.packets.serializers import serialize_packet, deserialize_packet
import json

# Serialize to a JSON-compatible dict
data = serialize_packet(packet)
json_string = json.dumps(data, indent=2)

# Deserialize from dict
packet2 = deserialize_packet(data)

# Or use the json_io helpers for file-based I/O
from gltg.integrations.json_io import save_packet_to_json

save_packet_to_json(packet, "output/my_packet.json")
```

The serializer uses `packet.model_dump(mode="json")` from Pydantic v2, which ensures all `date`, `datetime`, and `Enum` fields are serialized as JSON-safe strings.

---

## CLI Usage

GLTG provides a `gltg` CLI command with two subcommands.

### evaluate

```bash
# Print full JSON packet
gltg evaluate path/to/order.json

# Print human-readable summary
gltg evaluate path/to/order.json --summary

# Save packet to file
gltg evaluate path/to/order.json -o output/packet.json
```

### reforecast

```bash
# Reforecast an existing packet with new events
gltg reforecast output/packet.json path/to/events.json --summary

# Save updated packet
gltg reforecast output/packet.json path/to/events.json -o output/updated_packet.json
```

---

## Notes for Agent Integration

- All GLTG models are Pydantic v2 `BaseModel` subclasses. Use `model_validate()` to construct from dicts and `model_dump(mode="json")` to serialize.
- The engine is stateless and thread-safe. Create one `LeadTimeGraphEngine` instance and reuse it across requests.
- `date.today()` is used internally as the scheduling start date. In production agent code, you may want to inject a fixed reference date for reproducibility in testing.
- The `dynamic_form` field on `ApparelOrderInput` is a pass-through dict for buyer-supplied form fields. It is not validated by GLTG but is available for custom validators or downstream processing.
- Risk flags are deduplicated by `code`. The same `RiskFlagCode` will not appear twice in `packet.risk_flags`.
