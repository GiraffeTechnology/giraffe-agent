# Demo Runbook — Giraffe Agent B+M MVP

## Prerequisites

- Python 3.11+
- `uv` (recommended) or `pip`

## Installation

```bash
git clone https://github.com/GiraffeTechnology/giraffe-agent.git
cd giraffe-agent

# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt   # if available
# or install from pyproject.toml
pip install pydantic pydantic-settings fastapi uvicorn sqlalchemy \
            alembic aiosqlite python-dotenv httpx
```

## Running Tests

```bash
# B-side integration tests (33 scenarios)
python apps/bside/run_tests.py

# B-side pytest suite (222 tests)
pytest apps/bside/tests/ -q

# M-side pytest suite (177 tests)
pytest apps/mside/tests/ -q
```

Expected baseline:
- B-side run_tests.py: 33/33 passed
- B-side pytest: 222 passed
- M-side pytest: 177 passed

## Starting the API Server

```bash
uv run uvicorn api.main:app --reload
# or
uvicorn api.main:app --reload
```

Interactive API docs available at: http://localhost:8000/docs

## Demo Flow: Full B+M Procurement Cycle

### Step 1 — B-side: Create Workspace and Structure Requirement

```bash
curl -X POST http://localhost:8000/api/b-side/workspaces \
  -H "Content-Type: application/json" \
  -d '{"raw_requirement": "100 pcs aluminum 6061 CNC bracket, tolerance ±0.05 mm, delivery before September 30, to Munich"}'
```

Response:
```json
{"b_workspace_id": "bw_XXXXXXXXXXXX", "status": "created", ...}
```

```bash
# Structure the requirement (save b_workspace_id from above)
BW_ID="bw_XXXXXXXXXXXX"

curl -X POST http://localhost:8000/api/b-side/workspaces/$BW_ID/structure-requirement
```

### Step 2 — B-side: Draft Supplier Inquiry

```bash
curl -X POST http://localhost:8000/api/b-side/workspaces/$BW_ID/draft-inquiry \
  -H "Content-Type: application/json" \
  -d '{"supplier_ids": ["sup_001", "sup_002", "sup_003"]}'
```

### Step 3 — B+M Bridge: Dispatch to Suppliers

```bash
curl -X POST http://localhost:8000/api/bm/dispatch-inquiry \
  -H "Content-Type: application/json" \
  -d "{\"b_workspace_id\": \"$BW_ID\", \"supplier_ids\": [\"sup_001\", \"sup_002\"], \"channel\": \"mock\"}"
```

### Step 4 — M-side: Simulate Supplier Response

```bash
# Get m_workspace_id from dispatch response
MW_ID="mw_XXXXXXXXXXXX"

curl -X POST http://localhost:8000/api/m-side/workspaces/$MW_ID/message \
  -H "Content-Type: application/json" \
  -d '{"text": "可以做，30天交货，单价USD 12.50，MOQ 500，有QC照片更新", "attachments": []}'

curl -X POST http://localhost:8000/api/m-side/workspaces/$MW_ID/normalize-response
```

### Step 5 — B-side: Run Feasibility Simulation

```bash
curl -X POST http://localhost:8000/api/b-side/workspaces/$BW_ID/run-feasibility
```

Response includes ranked `DeliveryPath` list.

### Step 6 — Create Order

```bash
# After buyer selects a path_id from feasibility report
curl -X POST http://localhost:8000/api/bm/create-order-execution \
  -H "Content-Type: application/json" \
  -d "{\"b_workspace_id\": \"$BW_ID\", \"selected_path_id\": \"PATH-XXXXXXXX\"}"
```

### Step 7 — M-side: Acknowledge Order

```bash
ORD_ID="ORD-XXXXXXXX"

curl -X POST http://localhost:8000/api/m-side/orders/$ORD_ID/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"supplier_message": "确认接单，预计9月10日开工，9月25日交货。"}'
```

## Running the Demo Scripts

```bash
# Full B+M E2E demo
python scripts/run_bm_e2e_mvp.py

# Role switching demo
python scripts/run_role_switching_mvp.py

# Logistics tracking demo
python scripts/run_logistics_cainiao_like_api_mvp.py
```

## Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "giraffe-agent"}
```

## Known Issue

M-side dispatch with unknown `supplier_ids` returns HTTP 200 with `ok=true`
and `dispatched=0` instead of an error. This is a known issue tracked for v0.2.0.
See `docs/ROADMAP.md`.
