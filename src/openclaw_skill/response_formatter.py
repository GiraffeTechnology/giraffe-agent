"""
OpenClaw skill response formatter — formats action responses for B-side and M-side.
"""


from __future__ import annotations
def format_ok(data: dict | None = None, message: str | None = None) -> dict:
    """Format a successful response."""
    resp: dict = {"ok": True}
    if message:
        resp["message"] = message
    if data:
        resp.update(data)
    return resp


def format_error(error: str, code: str | None = None) -> dict:
    """Format an error response."""
    resp: dict = {"ok": False, "error": error}
    if code:
        resp["code"] = code
    return resp


def format_workspace(workspace) -> dict:
    """Format a BWWorkspace for API response."""
    return workspace.model_dump(mode="json")


def format_requirement(req) -> dict:
    """Format a BuyerRequirement for API response."""
    return req.model_dump(mode="json")
