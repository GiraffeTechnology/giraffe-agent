# Admin Manual — Giraffe Agent v1.0

---

## Chapter 1: System Architecture

Giraffe Agent v1.0 is a FastAPI application backed by PostgreSQL 16 with async SQLAlchemy 2.x. It uses:

- **API Layer:** FastAPI with async routes, OAuth2 JWT auth
- **ORM:** SQLAlchemy 2.x `Mapped` + `mapped_column`
- **Database:** PostgreSQL 16 with asyncpg driver
- **Migrations:** Alembic
- **LLM:** Pluggable (LocalStub / OpenAI / Qwen) via `get_llm_provider()`
- **Package Manager:** `uv`

---

## Chapter 2: Installation and Setup

### 2.1 Prerequisites

- Python 3.11+
- PostgreSQL 16
- `uv` (Python package manager)

### 2.2 Clone and Install

```bash
git clone https://github.com/giraffetechnology/giraffe-agent
cd giraffe-agent
uv sync
```

### 2.3 Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required:
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — Long random string for JWT signing

Optional:
- `LLM_PROVIDER` — `stub` (default), `openai`, or `qwen`
- `OPENAI_API_KEY` — Required if `LLM_PROVIDER=openai`
- `QWEN_API_KEY` — Required if `LLM_PROVIDER=qwen`

### 2.4 Database Migration

```bash
uv run alembic upgrade head
```

### 2.5 Seed Reference Data

```bash
BASE_URL=http://localhost:8000 uv run python scripts/seed_reference_data.py
```

---

## Chapter 3: Running the Application

### 3.1 Development

```bash
uv run uvicorn api.main:app --reload
```

### 3.2 Docker

```bash
docker-compose up --build
```

The `docker-compose.yml` starts both the API and PostgreSQL.

### 3.3 Health Check

```http
GET /health
```

Returns `{"status": "ok"}`.

---

## Chapter 4: Security

### 4.1 JWT Authentication

All routes except `/health` and `/api/auth/login`/`/api/auth/register` require a valid JWT in the `Authorization: Bearer <token>` header.

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes).

### 4.2 RBAC

Route-level authorization is enforced via `get_current_user` dependency. Tenant isolation is enforced at the service layer — users can only access data belonging to their tenant.

### 4.3 Secrets Management

- Never commit `.env` to version control
- Rotate `SECRET_KEY` immediately if exposed
- Use environment variables or a secrets manager in production

---

## Chapter 5: Monitoring and Maintenance

### 5.1 Industrial Execution Graph

All platform events are stored in the `execution_events` table as an append-only audit trail. This table should never be truncated or have rows deleted.

```sql
SELECT event_type, occurred_at, payload
FROM execution_events
ORDER BY occurred_at DESC
LIMIT 100;
```

### 5.2 Running Tests

```bash
uv run pytest tests/api/ tests/unit/ -v
```

All 98 tests must pass.

### 5.3 V1 Acceptance Verification

```bash
BASE_URL=http://localhost:8000 uv run python scripts/verify_v1_product_readiness_5x.py
```

Expected output: `GIRAFFE V1 PRODUCT READINESS: 5/5 PASS`

### 5.4 Database Backup

Back up the PostgreSQL database regularly. The `execution_events` table is the system of record for all platform activity.

```bash
pg_dump -U giraffe apparel_textile > backup_$(date +%Y%m%d).sql
```
