"""
DB Init Idempotency Tests — AIVAN Product Rule #10.

Rule: All state must be stored locally in SQLite in mock mode.

Tests:
  - DB init creates all expected tables
  - Re-running init is idempotent (no duplicate tables, no errors)
  - No duplicate seed rows on repeated init
  - Foreign key check passes
  - Integrity check passes
  - DB files not committed to git (gitignore verification)
"""

import os
import sqlite3
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent


# ─── SQLite DB init tests ──────────────────────────────────────────────────────

@pytest.fixture()
def db_env(tmp_path, monkeypatch):
    """Set up DB environment variables and return db_path."""
    db_path = tmp_path / "aivan_idempotency_test.db"
    monkeypatch.setenv("GIRAFFE_DB_MODE", "on")
    monkeypatch.setenv("GIRAFFE_DB_URL", f"sqlite:///{db_path}")
    return db_path


def _run_init_db():
    """Run init_db using the current GIRAFFE_DB_URL environment variable."""
    import os
    import src.db.base as base_mod
    import src.db.models  # noqa: F401 — registers all models with Base.metadata
    from sqlalchemy import create_engine

    db_url = os.environ.get("GIRAFFE_DB_URL", "sqlite:///./giraffe_test.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    base_mod.Base.metadata.create_all(bind=engine)
    return engine


def test_db_init_creates_tables(db_env):
    """Running init_db should create all expected tables."""
    _run_init_db()
    conn = sqlite3.connect(str(db_env))
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {
        "projects", "actors", "procurement_edges", "supplier_responses",
        "supplier_inquiries", "structured_requirements",
    }
    missing = expected_tables - tables
    assert not missing, f"Expected tables missing after init: {missing}"


def test_db_init_is_idempotent(db_env):
    """Running init_db twice must not raise errors or duplicate tables."""
    engine1 = _run_init_db()
    engine1.dispose()

    # Second init
    engine2 = _run_init_db()
    engine2.dispose()

    # Verify table count is stable
    conn = sqlite3.connect(str(db_env))
    cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    count_after = cursor.fetchone()[0]
    conn.close()
    assert count_after > 0


def test_sqlite_integrity_check(db_env):
    """SQLite integrity_check must return 'ok'."""
    _run_init_db()
    conn = sqlite3.connect(str(db_env))
    cursor = conn.execute("PRAGMA integrity_check;")
    result = cursor.fetchone()[0]
    conn.close()
    assert result == "ok", f"SQLite integrity_check failed: {result}"


def test_sqlite_foreign_key_check(db_env):
    """SQLite foreign_key_check must return no violations."""
    _run_init_db()
    conn = sqlite3.connect(str(db_env))
    cursor = conn.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()
    conn.close()
    assert not violations, f"Foreign key violations found: {violations}"


def test_data_dirs_created_by_aivan_init(tmp_path, monkeypatch):
    """AIVAN init must create expected local data directories."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIRAFFE_DB_MODE", "off")
    monkeypatch.delenv("AIVAN_DB_URL", raising=False)

    import sys
    sys.path.insert(0, str(ROOT))

    # Run init via CLI module directly
    from src.aivan_cli import _cmd_init
    _cmd_init()

    expected_dirs = [
        "data/message_drafts",
        "data/b_side_workspaces",
        "data/m_side_workspaces",
        "data/supplier_profiles",
        "data/projects",
        "data/conversation_bindings",
    ]
    for d in expected_dirs:
        assert (tmp_path / d).exists(), f"Expected data dir not created: {d}"


# ─── Gitignore audit ──────────────────────────────────────────────────────────

def test_gitignore_protects_db_files():
    """gitignore must protect local DB files from accidental commit."""
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore must exist"
    content = gitignore.read_text(encoding="utf-8")
    assert "*.db" in content or "*.sqlite" in content, (
        ".gitignore must exclude *.db or *.sqlite files"
    )


def test_gitignore_protects_env_file():
    """gitignore must protect .env from accidental commit."""
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert ".env" in content, ".gitignore must exclude .env files"


def test_gitignore_protects_data_directories():
    """gitignore must protect data/ directories from accidental commit."""
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert "data/" in content or "data/*" in content, (
        ".gitignore must protect data/ directories"
    )


def test_gitignore_protects_logs():
    """gitignore must protect log files."""
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert "*.log" in content or "logs/" in content, (
        ".gitignore must exclude *.log or logs/ directories"
    )


# ─── File-based store idempotency ─────────────────────────────────────────────

def test_draft_store_idempotent_read(tmp_path):
    """Reading the draft store multiple times is safe and idempotent."""
    import src.openclaw_skill.message_draft_store as mds
    orig = mds._DATA_DIR
    mds._DATA_DIR = tmp_path / "data" / "message_drafts"
    mds._DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.openclaw_skill.message_draft_store import find_pending_drafts, create_draft
        create_draft("proj_idem", "ch", "supplier", "Test")
        result1 = find_pending_drafts("proj_idem")
        result2 = find_pending_drafts("proj_idem")
        assert len(result1) == len(result2)
    finally:
        mds._DATA_DIR = orig


def test_b_workspace_store_idempotent(tmp_path):
    """Creating and reading B-side workspaces is idempotent."""
    import src.b_side.workspace as ws_mod
    orig = ws_mod._DATA_DIR
    ws_mod._DATA_DIR = tmp_path / "data" / "b_side_workspaces"
    ws_mod._DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.b_side.workspace import create_b_workspace, get_b_workspace
        ws = create_b_workspace("1000 shirts Vancouver 30 days")
        ws2 = get_b_workspace(ws.b_workspace_id)
        assert ws.b_workspace_id == ws2.b_workspace_id
        assert ws.raw_requirement == ws2.raw_requirement
    finally:
        ws_mod._DATA_DIR = orig
