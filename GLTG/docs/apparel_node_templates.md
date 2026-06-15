# Apparel Node Templates

This document lists all 28 `ApparelNodeType` values supported by the GLTG engine, along with display names, typical participant types, baseline lead times, required inputs/outputs, and whether the node is optional in the standard workflow.

Baseline lead times are in **working days** at the p50/p80/p90 percentile bands for a typical 5,000-10,000 piece order. The SEWING baseline scales linearly with quantity (7 days per 1,000 pieces at p50).

---

## Node Reference Table

| # | Node Type | Display Name | Typical Participant | p50 | p80 | p90 | Required Inputs | Outputs | Optional? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `BUYER_REQUIREMENT_CONFIRMATION` | Buyer Requirement Confirmation | BUYER / BUYING_HOUSE | 2d | 3d | 5d | _(none)_ | `buyer_requirements` | No |
| 2 | `DESIGN_OR_TECH_PACK_CONFIRMATION` | Design / Tech Pack Confirmation | BUYER / BUYING_HOUSE | 3d | 5d | 7d | `buyer_requirements` | `tech_pack` | No |
| 3 | `FABRIC_SELECTION` | Fabric Selection | FABRIC_SUPPLIER / BUYER | 3d | 5d | 7d | `tech_pack` | `fabric_spec` | No |
| 4 | `FABRIC_AVAILABILITY_CONFIRMATION` | Fabric Availability Confirmation | FABRIC_SUPPLIER | 2d | 3d | 5d | `fabric_spec` | `fabric_availability` | No |
| 5 | `FABRIC_ORDERING` | Fabric Ordering | FABRIC_SUPPLIER | 21d | 28d | 35d | `fabric_availability` | `fabric_ordered` | No |
| 6 | `FABRIC_DYEING_OR_PRINTING` | Fabric Dyeing / Printing | FABRIC_SUPPLIER | 10d | 14d | 21d | `fabric_ordered` | `fabric_dyed` | **Yes** |
| 7 | `FABRIC_FINISHING` | Fabric Finishing | FABRIC_SUPPLIER | 5d | 7d | 10d | `fabric_dyed` | `fabric_finished` | **Yes** |
| 8 | `FABRIC_TESTING` | Fabric Testing | FABRIC_SUPPLIER / QC_INSPECTOR | 7d | 10d | 14d | `fabric_finished` | `fabric_tested` | **Yes** |
| 9 | `TRIM_SELECTION` | Trim Selection | TRIM_SUPPLIER / BUYING_HOUSE | 2d | 3d | 5d | `tech_pack` | `trim_spec` | No |
| 10 | `TRIM_AVAILABILITY_CONFIRMATION` | Trim Availability Confirmation | TRIM_SUPPLIER | 2d | 3d | 5d | `trim_spec` | `trim_availability` | No |
| 11 | `TRIM_ORDERING` | Trim Ordering | TRIM_SUPPLIER | 14d | 21d | 28d | `trim_availability` | `trims_ordered` | No |
| 12 | `PACKAGING_MATERIAL_CONFIRMATION` | Packaging Material Confirmation | PACKAGING_SUPPLIER / GARMENT_FACTORY | 2d | 3d | 5d | `tech_pack` | `packaging_ready` | No |
| 13 | `SAMPLE_MAKING` | Sample Making | GARMENT_FACTORY | 7d | 10d | 14d | `tech_pack`, `fabric_spec` | `sample_ready` | No |
| 14 | `SAMPLE_APPROVAL` | Sample Approval | BUYER / BUYING_HOUSE | 5d | 7d | 10d | `sample_ready` | `sample_approved` | No |
| 15 | `PP_SAMPLE_APPROVAL` | Pre-Production Sample Approval | BUYER / BUYING_HOUSE | 3d | 5d | 7d | `sample_approved` | `pp_approved` | **Yes** |
| 16 | `PRODUCTION_SLOT_BOOKING` | Production Slot Booking | GARMENT_FACTORY | 2d | 3d | 5d | `sample_approved` | `production_slot` | No |
| 17 | `CUTTING` | Cutting | GARMENT_FACTORY | 2d | 3d | 4d | `fabric_tested`, `production_slot` | `cut_panels` | No |
| 18 | `SEWING` | Sewing | GARMENT_FACTORY | _qty-scaled_ | _qty-scaled_ | _qty-scaled_ | `cut_panels`, `trims_ordered` | `sewn_garments` | No |
| 19 | `WASHING_OR_FINISHING` | Washing / Finishing | GARMENT_FACTORY | 3d | 5d | 7d | `sewn_garments` | `finished_garments` | **Yes** |
| 20 | `INLINE_QC` | Inline Quality Control | QC_INSPECTOR | 1d | 2d | 3d | `sewn_garments` | `inline_qc_passed` | **Yes** |
| 21 | `FINAL_QC` | Final Quality Control | QC_INSPECTOR | 2d | 3d | 4d | `finished_garments` | `qc_approved` | No |
| 22 | `REWORK_IF_NEEDED` | Rework If Needed | GARMENT_FACTORY | 3d | 5d | 7d | `qc_approved` | `rework_done` | **Yes** |
| 23 | `PACKING` | Packing | GARMENT_FACTORY | 2d | 3d | 4d | `qc_approved`, `packaging_ready` | `packed` | No |
| 24 | `LOGISTICS_BOOKING` | Logistics Booking | LOGISTICS_PROVIDER | 3d | 5d | 7d | `sample_approved` | `logistics_booked` | No |
| 25 | `CUSTOMS_OR_EXPORT_DOCS` | Customs / Export Documentation | LOGISTICS_PROVIDER / BUYING_HOUSE | 2d | 3d | 5d | `packed` | `customs_cleared` | No |
| 26 | `SHIPMENT` | Shipment | LOGISTICS_PROVIDER | 21d | 28d | 35d | `customs_cleared`, `logistics_booked` | `shipped` | No |
| 27 | `BUYER_RECEIPT` | Buyer Receipt | BUYER | 1d | 2d | 3d | `shipped` | `received` | No |
| 28 | `BUYER_SIGN_OFF` | Buyer Sign-Off | BUYER | 2d | 3d | 5d | `received` | `signed_off` | **Yes** |

---

## SEWING Baseline Scaling Formula

SEWING is the only node with a quantity-dependent baseline. The formula is:

```
p50 = max(1, round(quantity / 1000 * 7.0, 1))   # 7 days per 1,000 pieces
p80 = max(1, round(p50 * 1.4, 1))
p90 = max(1, round(p50 * 2.0, 1))
min = max(1, round(p50 * 0.7, 1))
max = max(1, round(p50 * 3.0, 1))
```

Examples at common quantities:

| Quantity | p50 | p80 | p90 |
|---|---|---|---|
| 500 | 3.5d | 4.9d | 7.0d |
| 1,000 | 7.0d | 9.8d | 14.0d |
| 2,000 | 14.0d | 19.6d | 28.0d |
| 5,000 | 35.0d | 49.0d | 70.0d |
| 10,000 | 70.0d | 98.0d | 140.0d |

These baselines are refined by the `DurationEstimator` when participant capacity data is available. The capacity-based formula (`quantity / capacity_per_day`) often yields shorter estimates for high-capacity factories.

---

## Optional Node Activation Rules

Optional nodes are included in the graph only when the order's `dynamic_form` or participant capabilities indicate they are required:

| Node | Included When |
|---|---|
| `FABRIC_DYEING_OR_PRINTING` | `dynamic_form.color != "white"` or dyeing explicitly required |
| `FABRIC_FINISHING` | Follows dyeing/printing in the workflow if dyeing is active |
| `FABRIC_TESTING` | `dynamic_form.lab_test_required == true` or fabric supplier has FABRIC_TESTING capability |
| `PP_SAMPLE_APPROVAL` | Buyer requires pre-production sign-off (set in dynamic_form) |
| `WASHING_OR_FINISHING` | `dynamic_form.wash_required == true` |
| `INLINE_QC` | QC_INSPECTOR participant has INLINE_QC capability |
| `REWORK_IF_NEEDED` | Always modelled as optional (triggered by QC outcome) |
| `BUYER_SIGN_OFF` | Buyer explicitly requires final acceptance event |
