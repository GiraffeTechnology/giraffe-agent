# Patent Alignment Matrix — Giraffe Agent v1.0

**Patents covered:**
- CN ZL 2023 1 1645939.9 / CN 117670482 B — 基于多方配合的C2M模式的纺织品及服装定制运营平台系统
- JP P7644545 / 特許第7644545号 — 協働型C2Mモデルに基づく繊維及びアパレルカスタマイズ運用プラットフォームシステム

---

## Patent Unit Mapping

| # | Patent Unit | Product Module | Files |
|---|---|---|---|
| 1 | Multi-party C2M order execution workflow | Order state machine (12 states) | `src/orders/state_machine.py`, `src/order_confirmation/service.py` |
| 2 | Buyer inquiry intake and structured form generation | Dynamic form generation with LLM extraction | `src/dynamic_forms/`, `api/routes/dynamic_forms.py` |
| 3 | Participant role classification and capability profiling | Participant registry with role-based classification | `src/participants/`, `src/db/models/participant.py` |
| 4 | Multi-dimensional supplier matching algorithm | 12-dimension matching scorer | `src/matching/scorer.py`, `src/matching/service.py` |
| 5 | RFQ drafting, approval gate, and sending workflow | RFQ state machine + approval gate pattern | `src/rfq/`, `src/approval_gates/` |
| 6 | Supplier response normalization and comparison | LLM-assisted response normalization + decision packets | `src/supplier_responses/`, `src/decision_packets/` |
| 7 | Lead time calculation (parallel + sequential) | Lead time calculator with missing-value safety | `src/lead_time/calculator.py` |
| 8 | Production monitoring with 12-milestone tracking | Milestone tracking + delay predictor | `src/milestones/`, `src/production_monitoring/` |
| 9 | Quality inspection evaluation and incident management | QC standard evaluation + quality ledger | `src/apparel_inspection/`, `src/qc/`, `src/quality_ledger/` |
| 10 | Supplier memory and quality replacement alert system | Supplier memory + replacement alert at 3 incidents | `src/supplier_memory/`, `src/replacement_alerts/` |

---

## Approval Gate Coverage

All external actions in the platform require human approval before execution, implementing the patent's approval gate requirement:

| Action | Approval Type | Enforced In |
|---|---|---|
| Send RFQ to supplier | RFQ_SEND | `src/rfq/service.py` |
| Approve supplier quote | QUOTE_APPROVE | `src/decision_packets/service.py` |
| Confirm order | ORDER_CONFIRM | `src/order_confirmation/service.py` |
| Send expedite alert | EXPEDITE_NOTIFY | `src/production_monitoring/service.py` |
| Notify participant replacement | PARTICIPANT_REPLACE | `src/replacement_alerts/service.py` |
| Buyer sign-off | BUYER_SIGNOFF | `src/order_confirmation/service.py` |

---

## Industrial Execution Graph

The append-only `ExecutionEvent` audit trail implements the Industrial Execution Graph concept from the patents, recording all platform events with immutable timestamps and full payloads.

- Writer: `src/execution_graph/writer.py`
- Reader: `src/execution_graph/service.py`
- API: `api/routes/execution_graph.py`
- 31 event types: `src/execution_graph/event_types.py`
