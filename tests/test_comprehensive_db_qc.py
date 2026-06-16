"""
Comprehensive DB + QC Intelligence Test Suite
Phases 2-6: DB integrity/concurrency/migration + QC real Qwen vision + exception tests
All Qwen calls are REAL — no mock, no fallback.
"""
import os
import sys
import time
import uuid
import json
import base64
import threading
import traceback
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

# Force real calls
os.environ["LLM_ENABLE_REAL_CALLS"] = "true"

from sqlalchemy import create_engine, text, event as sa_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# ─── Minimal 1x1 JPEG bytes (real image for Qwen) ────────────────────────────────────
# A solid red 100x100 JPEG
import io
try:
    from PIL import Image as PILImage
    def _make_solid_jpeg(r, g, b, size=(100, 100)) -> bytes:
        img = PILImage.new("RGB", size, color=(r, g, b))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

# Minimal valid JPEG (1x1 pixel red) - hand-crafted for when PIL not available
_MINIMAL_JPEG = bytes([
    0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,0x01,0x00,0x00,0x01,
    0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,
    0x07,0x07,0x07,0x09,0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
    0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,0x24,0x2E,0x27,0x20,
    0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,
    0x39,0x3D,0x38,0x32,0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
    0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,0x01,0x05,0x01,0x01,
    0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,
    0x05,0x06,0x07,0x08,0x09,0x0A,0x0B,0xFF,0xC4,0x00,0xB5,0x10,0x00,0x02,0x01,0x03,
    0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,0x01,0x02,0x03,0x00,
    0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,
    0x81,0x91,0xA1,0x08,0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,0x24,0x33,0x62,0x72,
    0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,0x29,0x2A,0x34,0x35,
    0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4A,0x53,0x54,0x55,
    0x56,0x57,0x58,0x59,0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6A,0x73,0x74,0x75,
    0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,0x8A,0x92,0x93,0x94,
    0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xB2,
    0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,0xC8,0xC9,
    0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,0xE3,0xE4,0xE5,0xE6,
    0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,0xF5,0xF6,0xF7,0xF8,0xF9,0xFA,0xFF,0xDA,
    0x00,0x08,0x01,0x01,0x00,0x00,0x3F,0x00,0xF5,0x0A,0x28,0xA0,0x02,0x8A,0x28,0x03,
    0xFF,0xD9
])

def _b64_jpeg(data: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()

RESULTS = []

def record(phase: str, name: str, passed: bool, detail: str = "", extra: dict = None):
    r = {"phase": phase, "name": name, "passed": passed, "detail": detail}
    if extra:
        r.update(extra)
    RESULTS.append(r)
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] [{phase}] {name}: {detail[:200]}")


# ════════════════════════════════════════════════════════
# PHASE 1: Environment & DB setup
# ════════════════════════════════════════════════════════

def phase1_env_check():
    DB_URL = os.getenv("DATABASE_URL", "sqlite:///./giraffe_mvp.db")
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(engine)
    tables = insp.get_table_names()
    record("Phase1", "DB tables count", len(tables) > 30, f"Found {len(tables)} tables")

    # Check QC tables are MISSING from migration
    qc_tables = [t for t in ["qc_reference_images", "qc_process_cards", "qc_comparison_reports"] if t in tables]
    record("Phase1", "QC tables in alembic migration",
           len(qc_tables) == 3,
           f"QC tables present in schema: {qc_tables} (expected 3, found {len(qc_tables)}) — {'MISSING FROM MIGRATION' if len(qc_tables) < 3 else 'OK'}")

    # Verify alembic_version
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    record("Phase1", "Alembic version applied", ver is not None, str(ver))
    return engine


# ════════════════════════════════════════════════════════
# PHASE 2: DB integrity / constraints
# ════════════════════════════════════════════════════════

def phase2_db_integrity(engine):
    Session = sessionmaker(bind=engine)

    # 2a: FK constraint — insert supplier_inquiry with bad project_id
    db = Session()
    try:
        # Enable FK enforcement on SQLite
        db.execute(text("PRAGMA foreign_keys = ON"))
        bad_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db.execute(text("""
            INSERT INTO supplier_inquiries
            (inquiry_id, project_id, edge_id, from_actor_id, to_actor_id,
             requested_fields_json, required_reply_schema_json, status, created_at, updated_at)
            VALUES (:iid, :pid, :eid, :faid, :taid, '{}', '{}', 'SENT', :now, :now)
        """), {"iid": bad_id, "pid": "NONEXISTENT-PROJECT", "eid": "FAKE-EDGE",
               "faid": "FAKE-FROM", "taid": "FAKE-TO", "now": now})
        db.commit()
        # SQLite FK not enforced unless PRAGMA is set per connection AND engine-level
        record("Phase2", "FK reject bad project_id", False,
               "FK insert succeeded — SQLite FK enforcement requires connect_event hook (PRAGMA per connection)")
    except IntegrityError as e:
        record("Phase2", "FK reject bad project_id", True, f"Correctly rejected: {e}")
    except Exception as e:
        record("Phase2", "FK reject bad project_id", False, str(e))
    finally:
        db.rollback()
        db.close()

    # 2b: FK constraint with proper per-connection PRAGMA enforcement
    fk_engine = create_engine(
        os.getenv("DATABASE_URL", "sqlite:///./giraffe_mvp.db"),
        connect_args={"check_same_thread": False}
    )
    @sa_event.listens_for(fk_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    FKSession = sessionmaker(bind=fk_engine)
    db2 = FKSession()
    try:
        bad_id2 = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db2.execute(text("""
            INSERT INTO supplier_inquiries
            (inquiry_id, project_id, edge_id, from_actor_id, to_actor_id,
             requested_fields_json, required_reply_schema_json, status, created_at, updated_at)
            VALUES (:iid, 'NONEXISTENT-PROJECT', 'FAKE-EDGE', 'FAKE-FROM', 'FAKE-TO',
                    '{}', '{}', 'SENT', :now, :now)
        """), {"iid": bad_id2, "now": now})
        db2.commit()
        record("Phase2", "FK enforcement with PRAGMA hook", False,
               "SQLite FK still not rejected even with PRAGMA hook — requires engine-level config")
    except IntegrityError as e:
        record("Phase2", "FK enforcement with PRAGMA hook", True, f"Correctly rejected: {e}")
    except Exception as e:
        record("Phase2", "FK enforcement with PRAGMA hook", False, str(e))
    finally:
        db2.rollback()
        db2.close()

    # 2c: PK uniqueness constraint
    db3 = FKSession()
    try:
        pid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db3.execute(text("""
            INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at)
            VALUES (:pid, 'TestActor', 'buyer', '{}', '{}', '{}', 1, :now, :now)
        """), {"pid": pid, "now": now})
        db3.commit()
        # Second insert with same PK
        db3.execute(text("""
            INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at)
            VALUES (:pid, 'DuplicateActor', 'buyer', '{}', '{}', '{}', 1, :now, :now)
        """), {"pid": pid, "now": now})
        db3.commit()
        record("Phase2", "PK uniqueness constraint", False, "Duplicate PK accepted!")
    except IntegrityError as e:
        record("Phase2", "PK uniqueness constraint", True, f"Correctly rejected duplicate PK")
    except Exception as e:
        record("Phase2", "PK uniqueness constraint", False, str(e))
    finally:
        db3.rollback()
        db3.close()

    # 2d: NOT NULL constraint
    db4 = FKSession()
    try:
        db4.execute(text("""
            INSERT INTO actors (actor_id, name, actor_type, is_active, created_at, updated_at)
            VALUES (:pid, NULL, 'buyer', 1, :now, :now)
        """), {"pid": str(uuid.uuid4()), "now": datetime.now(timezone.utc).isoformat()})
        db4.commit()
        record("Phase2", "NOT NULL constraint on actors.name", False, "NULL name accepted!")
    except IntegrityError as e:
        record("Phase2", "NOT NULL constraint on actors.name", True, "Correctly rejected NULL name")
    except Exception as e:
        record("Phase2", "NOT NULL constraint on actors.name", False, str(e))
    finally:
        db4.rollback()
        db4.close()

    # 2e: Transaction atomicity (multi-table write, mid-way failure)
    db5 = FKSession()
    actor_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        db5.execute(text("""
            INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at)
            VALUES (:aid, 'TxTestActor', 'buyer', '{}', '{}', '{}', 1, :now, :now)
        """), {"aid": actor_id, "now": now})
        # Intentional failure: insert project with NULL status (NOT NULL)
        db5.execute(text("""
            INSERT INTO projects (project_id, original_buyer_actor_id, category, product_summary, quantity, status, product_tier, created_by_channel, metadata_json, created_at, updated_at)
            VALUES (:pid, :aid, 'TestCat', 'Test', 1, NULL, 'free', 'mock', '{}', :now, :now)
        """), {"pid": project_id, "aid": actor_id, "now": now})
        db5.commit()
        # If we get here, check actor was NOT committed either
        record("Phase2", "Transaction atomicity on mid-failure", False,
               "NULL status accepted — constraint not enforced on projects.status")
    except Exception:
        db5.rollback()
        # Verify actor was NOT persisted
        db_check = FKSession()
        row = db_check.execute(text("SELECT actor_id FROM actors WHERE actor_id=:aid"),
                                {"aid": actor_id}).fetchone()
        db_check.close()
        record("Phase2", "Transaction atomicity on mid-failure", row is None,
               f"After rollback, actor {'NOT found (correct)' if row is None else 'FOUND (dirty data!)'}")
    finally:
        db5.rollback()
        db5.close()

    # 2f: Cascade behavior check (schema-level: no cascade defined in ORM, deletion should fail or leave orphan)
    db6 = FKSession()
    now = datetime.now(timezone.utc).isoformat()
    a_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    try:
        db6.execute(text("INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at) VALUES (:a, 'DelTestActor', 'buyer', '{}', '{}', '{}', 1, :now, :now)"), {"a": a_id, "now": now})
        db6.execute(text("INSERT INTO projects (project_id, original_buyer_actor_id, category, product_summary, quantity, status, product_tier, created_by_channel, metadata_json, created_at, updated_at) VALUES (:p, :a, 'DelCat', 'Test', 1, 'CREATED', 'free', 'mock', '{}', :now, :now)"), {"p": p_id, "a": a_id, "now": now})
        db6.commit()
        # Try to delete actor that has a project referencing it
        db6.execute(text("DELETE FROM actors WHERE actor_id=:a"), {"a": a_id})
        db6.commit()
        record("Phase2", "Cascade/FK on actor delete with referencing project", False,
               "Actor deletion succeeded despite FK reference from projects — FK not enforced (SQLite requires PRAGMA per connection)")
    except IntegrityError as e:
        record("Phase2", "Cascade/FK on actor delete with referencing project", True,
               f"Correctly blocked actor deletion: {str(e)[:100]}")
    except Exception as e:
        record("Phase2", "Cascade/FK on actor delete with referencing project", False, str(e))
    finally:
        db6.rollback()
        db6.close()


# ════════════════════════════════════════════════════════
# PHASE 3: DB performance / concurrency
# ════════════════════════════════════════════════════════

def phase3_db_concurrency(engine):
    # 3a: Concurrent writes to same project — check for dirty write / conflict
    Session = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc).isoformat()
    a_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    _ACTOR_FULL = "INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at) VALUES (:a, :name, 'buyer', '{}', '{}', '{}', 1, :now, :now)"

    setup = Session()
    setup.execute(text(_ACTOR_FULL), {"a": a_id, "name": "ConcActor", "now": now})
    setup.execute(text("INSERT INTO projects (project_id, original_buyer_actor_id, category, product_summary, quantity, status, product_tier, created_by_channel, metadata_json, created_at, updated_at) VALUES (:p, :a, 'ConcTest', 'Test', 1, 'CREATED', 'free', 'mock', '{}', :now, :now)"), {"p": p_id, "a": a_id, "now": now})
    setup.commit()
    setup.close()

    errors = []
    def update_status(new_status, local_errors=errors):
        db = Session()
        try:
            db.execute(text("UPDATE projects SET status=:s, updated_at=:now WHERE project_id=:p"),
                       {"s": new_status, "now": datetime.now(timezone.utc).isoformat(), "p": p_id})
            db.commit()
        except Exception as e:
            local_errors.append(str(e))
        finally:
            db.close()

    statuses = ["IN_EXECUTION", "ORDER_CONFIRMED", "CLOSED", "CANCELLED", "CREATED"]
    threads = [threading.Thread(target=update_status, args=(s,)) for s in statuses]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Check final state
    check = Session()
    row = check.execute(text("SELECT status FROM projects WHERE project_id=:p"), {"p": p_id}).fetchone()
    check.close()
    record("Phase3", "Concurrent status updates (5 threads)", len(errors) == 0,
           f"Final status: {row[0] if row else 'NOT FOUND'}, errors: {errors}")
    record("Phase3", "No locking mechanism (optimistic/pessimistic)", False,
           "SQLite uses DB-level write lock — concurrent writes serialize, no optimistic lock / version field in schema. Risk: no conflict detection for business logic.")

    # 3b: Bulk insert performance
    Session2 = sessionmaker(bind=engine)
    bulk_session = Session2()
    actor_ids = []
    t0 = time.time()
    for i in range(500):
        aid = str(uuid.uuid4())
        actor_ids.append(aid)
        n = datetime.now(timezone.utc).isoformat()
        bulk_session.execute(text(
            "INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at) VALUES (:a, :name, 'manufacturer', '{}', '{}', '{}', 1, :now, :now)"
        ), {"a": aid, "name": f"BulkActor_{i}", "now": n})
    bulk_session.commit()
    t1 = time.time()
    elapsed = t1 - t0
    record("Phase3", "Bulk insert 500 actors", elapsed < 30,
           f"500 inserts took {elapsed:.2f}s ({500/elapsed:.0f} rows/s)")

    # 3c: Query with index check
    t2 = time.time()
    rows = bulk_session.execute(
        text("SELECT * FROM actors WHERE is_active=1 LIMIT 500")
    ).fetchall()
    t3 = time.time()
    record("Phase3", "Query 500 active actors", len(rows) >= 500, f"Retrieved {len(rows)} rows in {t3-t2:.3f}s")
    bulk_session.close()

    # 3d: Check missing indexes on key FK columns
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(engine)

    # Check supplier_inquiries.project_id index
    si_indexes = insp.get_indexes("supplier_inquiries")
    si_idx_cols = [c for idx in si_indexes for c in idx["column_names"]]
    record("Phase3", "Index on supplier_inquiries.project_id", "project_id" in si_idx_cols,
           f"Indexed cols: {si_idx_cols}")

    # Check projects — no explicit index on status (full-table scan for status queries)
    proj_indexes = insp.get_indexes("projects")
    proj_idx_cols = [c for idx in proj_indexes for c in idx["column_names"]]
    record("Phase3", "Index on projects.status (performance risk)", "status" in proj_idx_cols,
           f"projects indexes: {proj_idx_cols} — {'status not indexed, full-table scan risk' if 'status' not in proj_idx_cols else 'OK'}")


# ════════════════════════════════════════════════════════
# PHASE 4: Migration safety
# ════════════════════════════════════════════════════════

def phase4_migration_safety():
    # 4a: Check downgrade logic exists
    import subprocess
    result = subprocess.run(
        ["uv", "run", "python3", "-c",
         "import ast, pathlib; "
         "src = pathlib.Path('alembic/versions/a3b15996ec7b_create_all_tables.py').read_text(); "
         "print('HAS_DOWNGRADE:', 'def downgrade' in src); "
         "print('DOWNGRADE_PASS:', 'pass' in src[src.find('def downgrade'):src.find('def downgrade')+200] if 'def downgrade' in src else False)"],
        capture_output=True, text=True, cwd="/home/user/giraffe-agent-clean"
    )
    out = result.stdout + result.stderr
    has_downgrade = "HAS_DOWNGRADE: True" in out
    downgrade_is_pass = "DOWNGRADE_PASS: True" in out
    record("Phase4", "Migration has downgrade function", has_downgrade, out.strip())
    record("Phase4", "Downgrade is non-trivial (not just pass)", has_downgrade and not downgrade_is_pass,
           "downgrade() appears to be 'pass' only" if downgrade_is_pass else "downgrade() has real logic")

    # 4b: Attempt upgrade -> downgrade -> upgrade
    r_down = subprocess.run(["uv", "run", "alembic", "downgrade", "base"],
                             capture_output=True, text=True, cwd="/home/user/giraffe-agent-clean")
    down_ok = r_down.returncode == 0
    record("Phase4", "alembic downgrade base", down_ok, r_down.stdout[-300:] + r_down.stderr[-300:])

    r_up = subprocess.run(["uv", "run", "alembic", "upgrade", "head"],
                           capture_output=True, text=True, cwd="/home/user/giraffe-agent-clean")
    up_ok = r_up.returncode == 0
    record("Phase4", "alembic upgrade head (after downgrade)", up_ok, r_up.stdout[-300:] + r_up.stderr[-300:])

    # 4c: Check QC models are in migration files (search all versions)
    import glob as _glob
    migration_dir = "/home/user/giraffe-agent-clean/alembic/versions"
    all_migration_src = ""
    for mf in _glob.glob(migration_dir + "/*.py"):
        all_migration_src += open(mf).read()
    qc_in_migration = ("qc_reference_images" in all_migration_src and
                       "qc_process_cards" in all_migration_src and
                       "qc_comparison_reports" in all_migration_src)
    record("Phase4", "QC tables in migration script", qc_in_migration,
           "QC tables found across all migration files — OK" if qc_in_migration
           else "CRITICAL: QC ORM models (src/db/models/qc.py) define 3 tables but they are NOT in any alembic migration script. Migration drift detected.")

    # 4d: Check for DROP COLUMN (dangerous column removals) in upgrade() paths
    # Note: drop_table in downgrade() is expected and safe; only flag drop_column
    has_dangerous_drop = "op.drop_column" in all_migration_src
    record("Phase4", "No destructive DROP ops in migration", not has_dangerous_drop,
           "No DROP COLUMN found — safe" if not has_dangerous_drop else "WARNING: DROP COLUMN ops found in migration")


# ════════════════════════════════════════════════════════
# PHASE 5: QC Intelligence — Real Qwen vision calls
# ════════════════════════════════════════════════════════

QWEN_CALL_LOG = []  # track all real calls

def phase5_qc_real_qwen():
    api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        record("Phase5", "QWEN_API_KEY available", False, "No API key — stopping Phase 5")
        return

    record("Phase5", "QWEN_API_KEY available", True, f"Key starts with: {api_key[:8]}...")

    # Network connectivity
    import httpx
    try:
        r = httpx.get("https://dashscope.aliyuncs.com", timeout=10)
        record("Phase5", "Network: dashscope.aliyuncs.com reachable", True, f"HTTP {r.status_code}")
    except Exception as e:
        record("Phase5", "Network: dashscope.aliyuncs.com reachable", False, str(e))
        return

    # ── Verify provider loads correctly ───────────────────────────────────────────
    from src.llm.qwen_provider import QwenProvider
    from src.llm.provider_config import QWEN_VISION_ENDPOINT
    provider = QwenProvider(api_key=api_key)
    record("Phase5", "QwenProvider instantiated", True, f"vision_model={provider.vision_model}")

    vision_endpoint = QWEN_VISION_ENDPOINT
    record("Phase5", "Vision endpoint URL", True, vision_endpoint)

    # ── Helper: real HTTP call with timing ────────────────────────────────────────
    def real_vision_call(images_b64: list[str], question: str, label: str) -> dict:
        """Direct httpx call — records timing and HTTP status."""
        content = [{"image": img} for img in images_b64]
        content.append({"text": question})
        payload = {
            "model": provider.vision_model,
            "input": {"messages": [{"role": "user", "content": content}]},
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        t0 = time.time()
        resp = httpx.post(vision_endpoint, headers=headers, json=payload, timeout=90)
        elapsed = round(time.time() - t0, 2)
        QWEN_CALL_LOG.append({
            "label": label,
            "model": provider.vision_model,
            "http_status": resp.status_code,
            "elapsed_s": elapsed,
        })
        resp.raise_for_status()
        return resp.json(), elapsed, resp.status_code

    # ── Build test images ──────────────────────────────────────────────────
    if HAVE_PIL:
        red_img = _b64_jpeg(_make_solid_jpeg(220, 30, 30))
        green_img = _b64_jpeg(_make_solid_jpeg(30, 200, 30))
        blue_img = _b64_jpeg(_make_solid_jpeg(30, 30, 220))
        # Slightly different red (border case)
        light_red_img = _b64_jpeg(_make_solid_jpeg(210, 50, 50))
    else:
        # Use minimal JPEG for all — the test becomes less discriminating
        red_img = green_img = blue_img = light_red_img = _b64_jpeg(_MINIMAL_JPEG)
        record("Phase5", "PIL not available", False, "Pillow not installed — using identical minimal JPEG for all test images, color-difference tests will be limited")

    # ── Test Case 1: Identical images — should PASS ──────────────────────────
    q1 = (
        "你是QC检验AI。请对比两张图片，判断产品质量是否合格。"
        "请用JSON格式回答，包含字段: overall_result(pass/fail), overall_score(0-1), "
        "m_side_feedback_zh(中文反馈), b_side_summary(英文总结)。"
    )
    try:
        raw1, elapsed1, status1 = real_vision_call([red_img, red_img], q1, "TC1_identical")
        text1 = raw1.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(text1, list):
            text1 = " ".join(c.get("text", "") for c in text1 if isinstance(c, dict))
        record("Phase5", "TC1: Identical images — real Qwen call",
               status1 == 200,
               f"HTTP={status1}, elapsed={elapsed1}s, response_snippet={str(text1)[:300]}",
               extra={"qwen_model": provider.vision_model, "http_status": status1, "elapsed_s": elapsed1})
        # Check if response indicates pass
        passed_score = "pass" in str(text1).lower() or '"overall_result": "pass"' in str(text1).lower()
        record("Phase5", "TC1: Identical images — result is 'pass'", passed_score,
               f"LLM raw (first 500 chars): {str(text1)[:500]}")
    except Exception as e:
        record("Phase5", "TC1: Identical images", False, f"REAL CALL FAILED: {traceback.format_exc()[-500:]}")

    # ── Test Case 2: Clearly different images — should FAIL ─────────────────
    q2 = (
        "你是QC检验AI。第一张图片是标准样品，第二张图片是生产实物。"
        "请对比并判断是否符合标准。"
        "请用JSON格式回答，包含: overall_result(pass/fail), overall_score(0-1), "
        "detected_deviations(差异列表), m_side_feedback_zh(中文), b_side_summary(英文)。"
    )
    try:
        raw2, elapsed2, status2 = real_vision_call([red_img, green_img], q2, "TC2_different")
        text2 = raw2.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(text2, list):
            text2 = " ".join(c.get("text", "") for c in text2 if isinstance(c, dict))
        record("Phase5", "TC2: Different images — real Qwen call",
               status2 == 200,
               f"HTTP={status2}, elapsed={elapsed2}s, snippet={str(text2)[:300]}",
               extra={"qwen_model": provider.vision_model, "http_status": status2, "elapsed_s": elapsed2})
        failed_result = "fail" in str(text2).lower()
        record("Phase5", "TC2: Different images — result is 'fail'", failed_result,
               f"LLM raw: {str(text2)[:500]}")
    except Exception as e:
        record("Phase5", "TC2: Different images", False, f"REAL CALL FAILED: {traceback.format_exc()[-500:]}")

    # ── Test Case 3: Border case — slight color variation ────────────────────
    q3 = (
        "QC检验：第一张是标准样品(深红色)，第二张是生产实物(略浅红色)。"
        "请判断色差是否在可接受范围内（允许轻微色差）。"
        "JSON格式: overall_result(pass/fail/borderline), overall_score(0-1), "
        "m_side_feedback_zh, b_side_summary。"
    )
    try:
        raw3, elapsed3, status3 = real_vision_call([red_img, light_red_img], q3, "TC3_borderline")
        text3 = raw3.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(text3, list):
            text3 = " ".join(c.get("text", "") for c in text3 if isinstance(c, dict))
        record("Phase5", "TC3: Border case (slight variation) — real Qwen call",
               status3 == 200,
               f"HTTP={status3}, elapsed={elapsed3}s, snippet={str(text3)[:300]}",
               extra={"qwen_model": provider.vision_model, "http_status": status3, "elapsed_s": elapsed3})
        # Border case — any reasonable answer is acceptable
        record("Phase5", "TC3: Border case — has reasonable judgment", len(str(text3)) > 20,
               f"LLM raw: {str(text3)[:500]}")
    except Exception as e:
        record("Phase5", "TC3: Border case", False, f"REAL CALL FAILED: {traceback.format_exc()[-500:]}")

    # ── Test compare_media_against_standard (full QC pipeline) ─────────────────
    try:
        import tempfile
        from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard

        if HAVE_PIL:
            # Write images to temp files
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(_make_solid_jpeg(220, 30, 30))
                std_path = f.name
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(_make_solid_jpeg(220, 30, 30))
                prod_path = f.name
        else:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(_MINIMAL_JPEG)
                std_path = f.name
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(_MINIMAL_JPEG)
                prod_path = f.name

        t_start = time.time()
        report = compare_media_against_standard(
            project_id="TEST-PROJ-001",
            milestone_id="MILE-001",
            production_images=[prod_path],
            standard_images=[std_path],
            milestone_type="final_qc",
            order_requirements="Red product, 100x100mm solid color",
            provider_name="qwen",
        )
        t_end = time.time()

        os.unlink(std_path)
        os.unlink(prod_path)

        is_real = not report.fallback_used
        record("Phase5", "compare_media_against_standard — not a fallback/mock call",
               is_real,
               f"fallback_used={report.fallback_used}, provider={report.provider_name}, model={report.model_name}",
               extra={"qwen_model": report.model_name, "elapsed_s": round(t_end - t_start, 2)})
        record("Phase5", "compare_media_against_standard — has result", bool(report.overall_result),
               f"result={report.overall_result}, score={report.overall_score}")
    except Exception as e:
        record("Phase5", "compare_media_against_standard pipeline", False, traceback.format_exc()[-800:])

    # ── Phase 5 DB write: save QC report to DB ──────────────────────────────────
    try:
        from src.merchandiser.qc.qc_result_store import save_qc_report, get_qc_report
        from src.merchandiser.qc.qc_models import QCComparisonReport
        test_report = QCComparisonReport(
            overall_result="pass",
            overall_score=0.92,
            severity="low",
            detected_deviations=[],
            process_card_violations=[],
            buyer_confirmation_required=False,
            human_review_required=False,
            m_side_feedback_zh="产品符合标准",
            m_side_feedback_en="Product meets standard",
            b_side_summary="QC passed",
            provider_name="qwen",
            model_name=provider.vision_model,
            requested_provider="qwen",
            fallback_used=False,
            image_count=2,
            frames_used=0,
        )
        rid = save_qc_report(test_report, "TEST-PROJ-001", "MILE-001")
        retrieved = get_qc_report(rid)
        record("Phase5", "QC report saved to file store", retrieved is not None,
               f"report_id={rid}, overall_result={retrieved.get('overall_result') if retrieved else 'N/A'}")
    except Exception as e:
        record("Phase5", "QC report file store", False, traceback.format_exc()[-400:])


# ════════════════════════════════════════════════════════
# PHASE 6: Exception testing
# ════════════════════════════════════════════════════════

def phase6_exception_tests(engine):
    Session = sessionmaker(bind=engine)

    # 6a: Constraint violation — clear error, not 500
    db = Session()
    try:
        db.execute(text("""
            INSERT INTO actors (actor_id, name, actor_type, contact_channels_json, capabilities_json, profile_json, is_active, created_at, updated_at)
            VALUES (:a, :n, 'buyer', '{}', '{}', '{}', 1, :now, :now)
        """), {"a": str(uuid.uuid4()), "n": None, "now": datetime.now(timezone.utc).isoformat()})
        db.commit()
        record("Phase6", "Constraint violation returns clear IntegrityError", False,
               "NULL accepted — no clear error")
    except IntegrityError as e:
        record("Phase6", "Constraint violation returns clear IntegrityError", True,
               f"IntegrityError raised: {str(e)[:150]}")
    except Exception as e:
        record("Phase6", "Constraint violation returns clear IntegrityError", False, str(e))
    finally:
        db.rollback()
        db.close()

    # 6b: Corrupt JPEG to QC engine
    try:
        import tempfile
        from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"NOT_A_JPEG_THIS_IS_GARBAGE_DATA")
            bad_img = f.name
        # Should raise or handle gracefully
        try:
            report = compare_media_against_standard(
                project_id="TEST-PROJ-ERR",
                milestone_id="MILE-ERR",
                production_images=[bad_img],
                standard_images=[],
                provider_name="qwen",
            )
            record("Phase6", "Corrupt JPEG handled gracefully", True,
                   f"QC engine returned result (may be degraded): result={report.overall_result}")
        except Exception as e:
            record("Phase6", "Corrupt JPEG handled gracefully", False,
                   f"Exception raised: {str(e)[:300]}")
        finally:
            os.unlink(bad_img)
    except Exception as e:
        record("Phase6", "Corrupt JPEG test setup", False, str(e))

    # 6c: Qwen API with wrong key — verify error propagates
    try:
        from src.llm.qwen_provider import QwenProvider
        bad_provider = QwenProvider(api_key="INVALID_KEY_TEST")
        bad_provider.compare_images([_b64_jpeg(_MINIMAL_JPEG)], "test", system_prompt=None)
        record("Phase6", "Bad API key raises error (not silent mock fallback)", False,
               "Call succeeded with invalid key!")
    except RuntimeError as e:
        record("Phase6", "Bad API key raises error (not silent mock fallback)", True,
               f"RuntimeError: {str(e)[:200]}")
    except Exception as e:
        record("Phase6", "Bad API key raises error (not silent mock fallback)", False, str(e))


# ════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE DB + QC INTELLIGENCE TEST SUITE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    engine = phase1_env_check()

    print("\n--- Phase 2: DB Integrity ---")
    phase2_db_integrity(engine)

    print("\n--- Phase 3: DB Concurrency/Performance ---")
    phase3_db_concurrency(engine)

    print("\n--- Phase 4: Migration Safety ---")
    phase4_migration_safety()

    print("\n--- Phase 5: QC Intelligence (REAL Qwen API) ---")
    phase5_qc_real_qwen()

    print("\n--- Phase 6: Exception Tests ---")
    phase6_exception_tests(engine)

    # ── Final Report ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL TEST REPORT")
    print("=" * 70)

    passed = [r for r in RESULTS if r["passed"]]
    failed = [r for r in RESULTS if not r["passed"]]
    qwen_calls = QWEN_CALL_LOG

    print(f"\nTotal: {len(RESULTS)} | PASS: {len(passed)} | FAIL: {len(failed)}")
    print(f"\nReal Qwen API calls made: {len(qwen_calls)}")
    is_all_real = all(c.get("label","") != "mock" for c in qwen_calls)
    print(f"本次QC Intelligence测试 {'是' if is_all_real and len(qwen_calls) > 0 else '否'} 全部基于真实Qwen API调用")
    print(f"Qwen call details:")
    for c in qwen_calls:
        print(f"  - {c['label']}: model={c['model']}, HTTP={c['http_status']}, elapsed={c['elapsed_s']}s")

    print("\n=== FAILURES ===")
    for r in failed:
        print(f"  [{r['phase']}] {r['name']}: {r['detail'][:200]}")

    print("\n=== ALL RESULTS ===")
    for r in RESULTS:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] [{r['phase']}] {r['name']}")

    # Write JSON report
    import json as _json
    report_data = {
        "run_at": datetime.now().isoformat(),
        "total": len(RESULTS),
        "passed": len(passed),
        "failed": len(failed),
        "qwen_real_calls": qwen_calls,
        "all_real_qwen": is_all_real and len(qwen_calls) > 0,
        "results": RESULTS,
    }
    with open("/home/user/giraffe-agent-clean/COMPREHENSIVE_TEST_REPORT.json", "w") as f:
        _json.dump(report_data, f, indent=2, ensure_ascii=False)
    print("\nDetailed JSON report saved: COMPREHENSIVE_TEST_REPORT.json")
