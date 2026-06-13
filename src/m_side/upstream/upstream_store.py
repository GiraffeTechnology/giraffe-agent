"""
Upstream store — file-based persistence for upstream inquiries, responses,
approval requests, and rollups used by the role-switching API routes.

Data layout:
  data/upstream/{project_id}/inquiries.json
  data/upstream/{project_id}/dependencies.json
  data/upstream/{project_id}/responses.json
  data/upstream/{project_id}/approvals.json
  data/upstream/{project_id}/options.json
  data/upstream/{project_id}/rollup.json
"""

import json
from pathlib import Path

_BASE = Path("data/upstream")


def _proj_dir(project_id: str) -> Path:
    d = _BASE / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Dependencies ──────────────────────────────────────────────────────────────

def store_dependencies(project_id: str, deps: list[dict]) -> None:
    _save(_proj_dir(project_id) / "dependencies.json", deps)


def load_dependencies(project_id: str) -> list[dict]:
    return _load(_proj_dir(project_id) / "dependencies.json")


# ── Inquiries ─────────────────────────────────────────────────────────────────

def store_inquiry(project_id: str, inquiry: dict) -> None:
    path = _proj_dir(project_id) / "inquiries.json"
    items = _load(path)
    items.append(inquiry)
    _save(path, items)


def load_inquiry(project_id: str, inquiry_id: str) -> dict | None:
    for item in _load(_proj_dir(project_id) / "inquiries.json"):
        if item.get("inquiry_id") == inquiry_id:
            return item
    return None


def load_inquiries(project_id: str) -> list[dict]:
    return _load(_proj_dir(project_id) / "inquiries.json")


# ── Responses ─────────────────────────────────────────────────────────────────

def store_response(project_id: str, response: dict) -> None:
    path = _proj_dir(project_id) / "responses.json"
    items = _load(path)
    items.append(response)
    _save(path, items)


def load_responses_for_inquiry(project_id: str, inquiry_id: str) -> list[dict]:
    return [r for r in _load(_proj_dir(project_id) / "responses.json")
            if r.get("inquiry_id") == inquiry_id]


def load_responses_for_dependency(project_id: str, dependency_id: str) -> list[dict]:
    return [r for r in _load(_proj_dir(project_id) / "responses.json")
            if r.get("dependency_id") == dependency_id]


# ── Options ───────────────────────────────────────────────────────────────────

def store_options(project_id: str, options: list[dict]) -> None:
    path = _proj_dir(project_id) / "options.json"
    existing = _load(path)
    # Replace options for the same dependency
    if options:
        dep_id = options[0].get("dependency_id")
        existing = [o for o in existing if o.get("dependency_id") != dep_id]
    existing.extend(options)
    _save(path, existing)


def load_options(project_id: str) -> list[dict]:
    return _load(_proj_dir(project_id) / "options.json")


def load_option(project_id: str, option_id: str) -> dict | None:
    for item in load_options(project_id):
        if item.get("option_id") == option_id:
            return item
    return None


# ── Approval requests ─────────────────────────────────────────────────────────

def store_approval_request(project_id: str, request: dict) -> None:
    path = _proj_dir(project_id) / "approvals.json"
    items = _load(path)
    items.append(request)
    _save(path, items)


def load_approval_request(project_id: str, approval_request_id: str) -> dict | None:
    for item in _load(_proj_dir(project_id) / "approvals.json"):
        if item.get("approval_request_id") == approval_request_id:
            return item
    return None


def load_approval_results(project_id: str) -> list[dict]:
    """Load all approved results (approvals with status=approved and approved_option set)."""
    results = []
    for item in _load(_proj_dir(project_id) / "approvals.json"):
        if item.get("status") == "approved" and item.get("approved_result"):
            results.append(item["approved_result"])
    return results


def update_approval_request(project_id: str, approval_request_id: str, update: dict) -> None:
    path = _proj_dir(project_id) / "approvals.json"
    items = _load(path)
    for item in items:
        if item.get("approval_request_id") == approval_request_id:
            item.update(update)
    _save(path, items)


# ── Rollup ────────────────────────────────────────────────────────────────────

def store_rollup(project_id: str, rollup: dict) -> None:
    _save(_proj_dir(project_id) / "rollup.json", [rollup])


def load_rollup(project_id: str) -> dict | None:
    items = _load(_proj_dir(project_id) / "rollup.json")
    return items[0] if items else None
