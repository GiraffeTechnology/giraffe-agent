# Deployment Guide — Giraffe Agent v1.0

---

## Chapter 1: Prerequisites

- Python 3.11+
- PostgreSQL 16+
- `uv` package manager
- Docker + Docker Compose (for containerized deployment)

---

## Chapter 2: Local Development Deployment

```bash
# 1. Clone repository
git clone https://github.com/giraffetechnology/giraffe-agent
cd giraffe-agent

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY

# 4. Run database migrations
uv run alembic upgrade head

# 5. Start the API server
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Verify health
curl http://localhost:8000/health
```

---

## Chapter 3: Docker Compose Deployment

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env as needed

# 2. Start all services
docker-compose up --build -d

# 3. Run migrations
docker-compose exec api uv run alembic upgrade head

# 4. Seed reference data
docker-compose exec api uv run python scripts/seed_reference_data.py

# 5. Verify
curl http://localhost:8000/health
```

---

## Chapter 4: Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL URL (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | Yes | — | JWT signing key (min 32 chars random) |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Token expiry |
| `LLM_PROVIDER` | No | `stub` | `stub`, `openai`, or `qwen` |
| `OPENAI_API_KEY` | Conditional | — | Required if `LLM_PROVIDER=openai` |
| `QWEN_API_KEY` | Conditional | — | Required if `LLM_PROVIDER=qwen` |
| `APP_ENV` | No | `development` | `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## Chapter 5: Database Setup

### 5.1 Create Database

```sql
CREATE USER giraffe WITH PASSWORD 'giraffe';
CREATE DATABASE apparel_textile OWNER giraffe;
```

### 5.2 Run Migrations

```bash
uv run alembic upgrade head
```

### 5.3 Verify Tables

Key tables: `tenants`, `users`, `participants`, `projects`, `orders`, `execution_events`, `approval_requests`, `milestones`, `qc_standards`, `qc_records`, `shipments`, `tracking_events`, `supplier_memory_records`, `replacement_alerts`

---

## Chapter 6: LLM Provider Configuration

The platform works without an LLM provider using the built-in `LocalStub`:

```
LLM_PROVIDER=stub
```

For production with OpenAI:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

For Qwen (Alibaba Cloud):

```
LLM_PROVIDER=qwen
QWEN_API_KEY=...
```

---

## Chapter 7: Running Tests

```bash
# Run all API and unit tests
uv run pytest tests/api/ tests/unit/ -v

# Run with coverage
uv run pytest tests/api/ tests/unit/ --cov=src --cov=api

# Run specific test file
uv run pytest tests/api/test_logistics.py -v
```

---

## Chapter 8: Production Considerations

### 8.1 Secret Key

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 8.2 Database Connection Pool

The platform uses `NullPool` for asyncpg to ensure event loop safety. For high-concurrency production use, configure `POOL_SIZE` and `MAX_OVERFLOW` in `src/db/base.py` if switching to a pool.

### 8.3 CORS

The default CORS configuration allows all origins (`*`). Restrict this in production:

```python
allow_origins=["https://your-frontend-domain.com"]
```

### 8.4 Reverse Proxy

Recommended: nginx or Caddy as a reverse proxy with TLS termination:

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Chapter 9: Acceptance Verification

After deployment, run the V1 acceptance test to verify the full workflow:

```bash
BASE_URL=https://api.yourdomain.com uv run python scripts/run_v1_acceptance_apparel_order.py
```

Expected: `GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: PASS`

For 5x readiness verification:

```bash
BASE_URL=https://api.yourdomain.com uv run python scripts/verify_v1_product_readiness_5x.py
```

Expected: `GIRAFFE V1 PRODUCT READINESS: 5/5 PASS`
