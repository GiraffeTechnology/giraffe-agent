# Roadmap

## v0.1.0-mvp (current) — MVP Baseline

**Status:** Released as developer preview / open-core starting point.

### What's In

- B-side AI Buyer: requirement structuring, bilingual inquiry drafting,
  feasibility simulation, supplier response intake
- M-side AI Merchandiser: workspace management, deterministic response
  normalization, order acknowledgement, production/QC/logistics updates
- B+M Bridge: inquiry dispatch, response push, order creation
- Neutral Actor Model with role resolver
- Industrial Execution Graph (JSONL event log)
- Logistics tracking (Cainiao-like aggregator model)
- Professional/Free CAD-CNC matching module
- Role-switching state machine
- OpenClaw skill manifest
- Bilingual (EN + ZH) throughout
- Flat JSON file storage (no external DB required)
- 222 B-side tests + 177 M-side tests + 33 integration scenarios

### Known Issues

1. **Unknown supplier dispatch returns incorrect HTTP 200**
   - `POST /api/bm/dispatch-inquiry` with unknown `supplier_ids` returns
     `{"ok": true, "dispatched": 0}` instead of HTTP 422 with
     `{"missing_supplier_ids": [...]}`.
   - **Fix:** Return 404/422 with `partial_success` and `missing_supplier_ids`.

2. **No authentication on API server**
   - All endpoints are public by default.
   - **Fix:** Add JWT/API key middleware in v0.2.0.

3. **Flat JSON file storage**
   - Not suitable for concurrent multi-user access.
   - **Fix:** Migrate to async PostgreSQL with SQLAlchemy + Alembic in v0.2.0.

4. **Deterministic-only parsing**
   - Response normalization uses regex; misses complex natural language.
   - **Fix:** Add optional LLM normalization layer in v0.2.0.

---

## v0.2.0 — Production Core

**Target:** Q3 2026

### Planned

- [ ] Fix unknown supplier dispatch to return 404/422 with `missing_supplier_ids`
- [ ] Add API authentication (JWT or API key)
- [ ] Migrate from JSON file storage to async PostgreSQL
- [ ] Optional LLM normalization layer (Claude claude-haiku-4-5 for response parsing)
- [ ] Full alembic migration history
- [ ] Rate limiting on API endpoints
- [ ] Retry logic for channel adapter failures
- [ ] Supplier memory search (semantic similarity)

---

## v0.3.0 — Multi-Project & Webhook

**Target:** Q4 2026

### Planned

- [ ] Multi-project concurrent execution
- [ ] Real-time webhook delivery for logistics events
- [ ] WeChat official account integration
- [ ] WhatsApp Business API integration
- [ ] OpenClaw v2 skill manifest (multi-modal attachments)
- [ ] Buyer-facing reporting dashboard

---

## v1.0.0 — Production Release

**Target:** 2027

### Planned

- [ ] Full production hardening
- [ ] SLA-backed supplier reliability scoring
- [ ] Certified B↔M bridge API (versioned, stable)
- [ ] Multi-tenant support
- [ ] Audit trail compliance export
- [ ] Full patent-licensed deployment guide

---

## Contribution Opportunities

Looking for contributors on:

- LLM normalization layer (v0.2.0)
- WeChat/WhatsApp adapter implementation
- Test fixtures for more industries (electronics, automotive, food packaging)
- Documentation in Mandarin Chinese

See `CONTRIBUTING.md` to get started.
