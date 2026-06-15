"""
AIVAN CLI — local-first AI trade salesperson assistant.

Commands:
  aivan --help          Show this help
  aivan init            Initialize local database and seed data
  aivan serve           Start the FastAPI server (default port 8000)
  aivan test            Run the full test suite (wraps pytest)
"""

import os
import sys


def _cmd_help() -> None:
    print(__doc__)


def _cmd_init() -> None:
    """Initialize local SQLite database and seed platform whitelist."""
    print("[AIVAN] Initializing local database...")

    db_url = os.environ.get("AIVAN_DB_URL", "")
    db_mode = os.environ.get("GIRAFFE_DB_MODE", "off")
    if db_url:
        os.environ["GIRAFFE_DB_MODE"] = "on"
        os.environ.setdefault("GIRAFFE_DB_URL", db_url)
        print(f"[AIVAN] DB mode: on  ({db_url})")
    else:
        print(f"[AIVAN] DB mode: {db_mode} (file-based / in-memory)")

    try:
        from scripts.init_db import init_db
        init_db()
    except Exception as exc:
        print(f"[AIVAN] DB init skipped or failed (DB_MODE=off is normal): {exc}")

    # Ensure data directories exist
    import pathlib
    for d in [
        "data/message_drafts",
        "data/b_side_workspaces",
        "data/m_side_workspaces",
        "data/supplier_profiles",
        "data/projects",
        "data/conversation_bindings",
    ]:
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)

    print("[AIVAN] Data directories initialized.")
    print("[AIVAN] init complete.")


def _cmd_serve() -> None:
    """Start the AIVAN FastAPI server."""
    import subprocess
    host = os.environ.get("AIVAN_HOST", "127.0.0.1")
    port = os.environ.get("AIVAN_PORT", "8000")
    print(f"[AIVAN] Starting server at http://{host}:{port}")
    cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", host, "--port", port]
    os.execv(sys.executable, cmd)


def _cmd_test() -> None:
    """Run the full AIVAN test suite via pytest."""
    import subprocess
    args = sys.argv[2:] if len(sys.argv) > 2 else ["--tb=short", "-q"]
    result = subprocess.run([sys.executable, "-m", "pytest"] + args)
    sys.exit(result.returncode)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        _cmd_help()
        return

    cmd = sys.argv[1]
    if cmd == "init":
        _cmd_init()
    elif cmd == "serve":
        _cmd_serve()
    elif cmd == "test":
        _cmd_test()
    else:
        print(f"[AIVAN] Unknown command: {cmd}")
        _cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
