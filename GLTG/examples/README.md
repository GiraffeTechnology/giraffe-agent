# GLTG Example Files

This directory contains example JSON files for testing and demonstrating the
Giraffe Lead-Time Graph (GLTG) engine.

## Files

### `10000_shirts_order.json`

A fully populated `ApparelOrderInput` representing a realistic 10,000-piece
men's cotton shirt order destined for Shenzhen, China on FOB terms. Includes:

- Five participants (fabric supplier, trim supplier, garment factory, QC
  inspector, logistics provider)
- Three supplier memory records from a prior 8,000-piece order
- Two supplier responses with confirmed lead times
- A working-day calendar configured for Asia/Shanghai
- Rich `dynamic_form` fields covering fabric spec, embellishment, packaging,
  and quality standards

Expected result: `FEASIBLE` or `LIMITED_OPTIONS` status with at least one
viable `DeliveryPathOption` and a populated `commitable_date`.

---

### `10000_shirts_participants.json`

A standalone JSON array containing the same five participant objects extracted
from `10000_shirts_order.json`. Useful for testing participant-loading logic
in isolation, or for injecting participants into another order programmatically.

---

### `10000_shirts_supplier_memory.json`

A standalone JSON array containing the three `SupplierMemoryRecord` objects
from `10000_shirts_order.json`. These historical records cover sewing, cutting,
and fabric ordering performance from a prior run and are used by the
`DurationEstimator` to apply memory-based adjustments.

---

### `10000_shirts_progress_events.json`

A JSON array of two in-flight `ProgressEvent` objects for order `ORD-2025-001`:

- `MATERIAL_DELAYED` -- fabric mill backlog adding 5 days
- `SUPPLIER_CONFIRMED` -- factory `FACT-001` confirmed production start date

Used to demonstrate and test the `engine.reforecast(packet, events)` API.

---

### `zero_suppliers.json`

A minimal valid `ApparelOrderInput` with **no participants**, no supplier
memory, and no supplier responses. The engine is expected to return:

- `status = NO_FEASIBLE_OPTION`
- `options = []` (zero options)

Use this file to verify that the engine gracefully handles the empty-supply
scenario and surfaces the appropriate `NO_FEASIBLE_OPTION` risk flag.

---

### `one_supplier.json`

An `ApparelOrderInput` with **exactly one garment factory** participant
providing CUTTING, SEWING, and PACKING capabilities. The engine is expected
to return:

- `status = LIMITED_OPTIONS`
- Exactly **one** `DeliveryPathOption`
- `LIMITED_COMPETITION` in `risk_flags` (only a single source for production)

Use this file to verify single-supplier path generation and the
`LIMITED_COMPETITION` risk flag logic.

---

### `two_suppliers.json`

An `ApparelOrderInput` with **two garment factory** participants, each
providing CUTTING, SEWING, and PACKING capabilities. The engine is expected
to return:

- `status = LIMITED_OPTIONS`
- Exactly **two** `DeliveryPathOption` objects (one per factory)
- `LIMITED_COMPARISON` in `risk_flags` (only two options available)

Use this file to verify dual-supplier path generation and the
`LIMITED_COMPARISON` risk flag logic.
