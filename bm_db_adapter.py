"""B/M-side database adapter with lazy-loaded repositories.

GIRAFFE_DB_MODE controls behaviour:
  off (default) — in-memory store; no DB installation required; ``import src``
                  is never triggered at module load time or in off-mode methods.
  on            — real SQLAlchemy repositories; GIRAFFE_DB_URL must point at a
                  migrated database.

All ``src.db.*`` imports live inside ``BMDbAdapter`` methods that are only
reached when ``self._mode == "on"``.  Importing this module at the top level
of any script is therefore safe regardless of whether giraffe_db is installed.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add project root to sys.path so that downstream ``import src`` works when
# this file is not on the default Python path.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Computed once at import time from the environment; callers that need to
# override it programmatically (e.g. verify_integration.py) may write
# ``bm_db_adapter.DB_MODE = "on"`` before instantiating BMDbAdapter.
DB_MODE: str = os.environ.get("GIRAFFE_DB_MODE", "off").lower()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# In-memory store (DB-off mode)
# ---------------------------------------------------------------------------


class _MemStore:
    """Dict-backed store used when GIRAFFE_DB_MODE=off."""

    def __init__(self) -> None:
        self.actors: Dict[str, dict] = {}
        self._actor_key: Dict[str, str] = {}   # "name:type" → actor_id
        self.projects: Dict[str, dict] = {}
        self._project_key: Dict[str, str] = {}  # "buyer_id:product_summary" → project_id
        self.requirements: Dict[str, dict] = {}
        self.inquiries: Dict[str, dict] = {}
        self.responses: Dict[str, dict] = {}
        self.rollups: Dict[str, dict] = {}
        self.edges: Dict[str, dict] = {}
        self.events: List[dict] = []

    def count_actors(self) -> int:
        return len(self.actors)

    def count_projects(self) -> int:
        return len(self.projects)

    def count_requirements(self) -> int:
        return len(self.requirements)

    def count_inquiries(self) -> int:
        return len(self.inquiries)

    def count_responses(self) -> int:
        return len(self.responses)

    def count_rollups(self) -> int:
        return len(self.rollups)

    def count_edges(self) -> int:
        return len(self.edges)

    def count_events(self) -> int:
        return len(self.events)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class BMDbAdapter:
    """Unified adapter over real repos (on) or in-memory store (off).

    Parameters
    ----------
    db_url:
        SQLAlchemy connection string.  Defaults to the GIRAFFE_DB_URL env var
        or ``sqlite:///./bm_integration.db``.  Ignored in off mode.
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        # Read DB_MODE from this module's namespace so that callers can patch
        # it before instantiation without touching the environment.
        self._mode: str = DB_MODE
        self._db_url: str = (
            db_url
            or os.environ.get("GIRAFFE_DB_URL", "sqlite:///./bm_integration.db")
        )
        self._session = None
        self._actor_repo = None
        self._project_repo = None
        self._requirement_repo = None
        self._inquiry_repo = None
        self._response_repo = None
        self._rollup_repo = None
        self._graph_repo = None
        self._event_repo = None
        self._mem = _MemStore()

        if self._mode == "on":
            self._connect()

    # ------------------------------------------------------------------
    # DB connection (on-mode only)
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        from sqlalchemy import create_engine, event as sa_event
        from sqlalchemy.orm import sessionmaker

        kwargs: dict = {}
        if self._db_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}

        engine = create_engine(self._db_url, echo=False, **kwargs)

        if self._db_url.startswith("sqlite"):
            @sa_event.listens_for(engine, "connect")
            def _set_pragma(dbapi_conn, _rec):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

        Session = sessionmaker(bind=engine)
        self._session = Session()
        self._load_repos()

    def _load_repos(self) -> None:
        from src.db.repositories.actor_repo import ActorRepo
        from src.db.repositories.project_repo import ProjectRepo
        from src.db.repositories.requirement_repo import RequirementRepo
        from src.db.repositories.inquiry_repo import InquiryRepo
        from src.db.repositories.response_repo import ResponseRepo
        from src.db.repositories.rollup_repo import RollupRepo
        from src.db.repositories.graph_repo import GraphRepo
        from src.db.repositories.execution_event_repo import ExecutionEventRepo

        self._actor_repo = ActorRepo(self._session)
        self._project_repo = ProjectRepo(self._session)
        self._requirement_repo = RequirementRepo(self._session)
        self._inquiry_repo = InquiryRepo(self._session)
        self._response_repo = ResponseRepo(self._session)
        self._rollup_repo = RollupRepo(self._session)
        self._graph_repo = GraphRepo(self._session)
        self._event_repo = ExecutionEventRepo(self._session)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def commit(self) -> None:
        if self._mode == "on" and self._session:
            self._session.commit()

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Actor
    # ------------------------------------------------------------------

    def get_or_create_actor(
        self,
        name: str,
        actor_type: str,
        **kwargs: Any,
    ) -> dict:
        """Idempotent: returns an existing actor with the same (name, type)."""
        if self._mode == "on":
            from src.db.models.actor import Actor

            existing = (
                self._session.query(Actor)
                .filter(Actor.name == name, Actor.actor_type == actor_type)
                .first()
            )
            if existing:
                return {
                    "actor_id": existing.actor_id,
                    "name": existing.name,
                    "actor_type": existing.actor_type,
                }
            actor = self._actor_repo.create_actor(
                name=name, actor_type=actor_type, **kwargs
            )
            return {
                "actor_id": actor.actor_id,
                "name": actor.name,
                "actor_type": actor.actor_type,
            }
        else:
            key = f"{name}:{actor_type}"
            if key not in self._mem._actor_key:
                actor_id = _new_id()
                self._mem._actor_key[key] = actor_id
                self._mem.actors[actor_id] = {
                    "actor_id": actor_id,
                    "name": name,
                    "actor_type": actor_type,
                }
            return self._mem.actors[self._mem._actor_key[key]]

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    def get_or_create_project(
        self,
        original_buyer_actor_id: str,
        project_key: str,
        **kwargs: Any,
    ) -> dict:
        """Idempotent: keyed by (original_buyer_actor_id, project_key).

        ``project_key`` maps to the ``product_summary`` column so callers can
        supply a stable human-readable token such as ``"polo-shirts-run-3"``.
        """
        if self._mode == "on":
            from src.db.models.project import Project

            existing = (
                self._session.query(Project)
                .filter(
                    Project.original_buyer_actor_id == original_buyer_actor_id,
                    Project.product_summary == project_key,
                )
                .first()
            )
            if existing:
                return {
                    "project_id": existing.project_id,
                    "original_buyer_actor_id": existing.original_buyer_actor_id,
                    "status": existing.status,
                }
            project = self._project_repo.create_project(
                original_buyer_actor_id=original_buyer_actor_id,
                product_summary=project_key,
                **kwargs,
            )
            return {
                "project_id": project.project_id,
                "original_buyer_actor_id": project.original_buyer_actor_id,
                "status": project.status,
            }
        else:
            key = f"{original_buyer_actor_id}:{project_key}"
            if key not in self._mem._project_key:
                project_id = _new_id()
                self._mem._project_key[key] = project_id
                self._mem.projects[project_id] = {
                    "project_id": project_id,
                    "original_buyer_actor_id": original_buyer_actor_id,
                    "product_summary": project_key,
                    "status": "CREATED",
                    **kwargs,
                }
            return self._mem.projects[self._mem._project_key[key]]

    def update_project_status(self, project_id: str, status: str) -> dict:
        if self._mode == "on":
            project = self._project_repo.update_project_status(project_id, status)
            return {"project_id": project.project_id, "status": project.status}
        else:
            self._mem.projects[project_id]["status"] = status
            return self._mem.projects[project_id]

    # ------------------------------------------------------------------
    # Structured Requirement
    # ------------------------------------------------------------------

    def create_requirement(
        self,
        project_id: str,
        source_actor_id: str,
        **kwargs: Any,
    ) -> dict:
        if self._mode == "on":
            req = self._requirement_repo.create_requirement(
                project_id=project_id,
                source_actor_id=source_actor_id,
                **kwargs,
            )
            return {
                "requirement_id": req.requirement_id,
                "project_id": req.project_id,
                "category": req.category,
                "quantity": req.quantity,
            }
        else:
            req_id = _new_id()
            record: dict = {
                "requirement_id": req_id,
                "project_id": project_id,
                "source_actor_id": source_actor_id,
                **kwargs,
            }
            self._mem.requirements[req_id] = record
            return record

    # ------------------------------------------------------------------
    # Procurement Edge
    # ------------------------------------------------------------------

    def create_edge(
        self,
        project_id: str,
        from_actor_id: str,
        to_actor_id: str,
        edge_type: str,
        inquiry_id: Optional[str] = None,
        response_id: Optional[str] = None,
        status: str = "DRAFT",
        **kwargs: Any,
    ) -> dict:
        if self._mode == "on":
            edge = self._graph_repo.create_edge(
                project_id=project_id,
                from_actor_id=from_actor_id,
                to_actor_id=to_actor_id,
                edge_type=edge_type,
                inquiry_id=inquiry_id,
                response_id=response_id,
                status=status,
                **kwargs,
            )
            return {
                "edge_id": edge.edge_id,
                "project_id": edge.project_id,
                "inquiry_id": edge.inquiry_id,
                "response_id": edge.response_id,
                "status": edge.status,
            }
        else:
            edge_id = _new_id()
            record = {
                "edge_id": edge_id,
                "project_id": project_id,
                "from_actor_id": from_actor_id,
                "to_actor_id": to_actor_id,
                "edge_type": edge_type,
                "inquiry_id": inquiry_id,
                "response_id": response_id,
                "status": status,
            }
            self._mem.edges[edge_id] = record
            return record

    def update_edge(self, edge_id: str, **kwargs: Any) -> dict:
        """Update arbitrary columns on a ProcurementEdge row."""
        if self._mode == "on":
            from src.db.models.procurement_edge import ProcurementEdge

            edge = (
                self._session.query(ProcurementEdge)
                .filter(ProcurementEdge.edge_id == edge_id)
                .first()
            )
            if edge is None:
                raise ValueError(f"ProcurementEdge not found: {edge_id}")
            for k, v in kwargs.items():
                setattr(edge, k, v)
            self._session.flush()
            return {
                "edge_id": edge.edge_id,
                "inquiry_id": edge.inquiry_id,
                "response_id": edge.response_id,
                "status": edge.status,
            }
        else:
            self._mem.edges[edge_id].update(kwargs)
            return self._mem.edges[edge_id]

    def get_edge(self, edge_id: str) -> dict:
        if self._mode == "on":
            edge = self._graph_repo.get_edge(edge_id)
            if edge is None:
                raise ValueError(f"ProcurementEdge not found: {edge_id}")
            return {
                "edge_id": edge.edge_id,
                "inquiry_id": edge.inquiry_id,
                "response_id": edge.response_id,
                "status": edge.status,
            }
        else:
            return self._mem.edges[edge_id]

    # ------------------------------------------------------------------
    # Supplier Inquiry
    # ------------------------------------------------------------------

    def create_inquiry(
        self,
        project_id: str,
        edge_id: str,
        from_actor_id: str,
        to_actor_id: str,
        **kwargs: Any,
    ) -> dict:
        if self._mode == "on":
            inq = self._inquiry_repo.create_supplier_inquiry(
                project_id=project_id,
                edge_id=edge_id,
                from_actor_id=from_actor_id,
                to_actor_id=to_actor_id,
                **kwargs,
            )
            return {
                "inquiry_id": inq.inquiry_id,
                "project_id": inq.project_id,
                "edge_id": inq.edge_id,
                "status": inq.status,
            }
        else:
            inq_id = _new_id()
            record = {
                "inquiry_id": inq_id,
                "project_id": project_id,
                "edge_id": edge_id,
                "from_actor_id": from_actor_id,
                "to_actor_id": to_actor_id,
                "status": kwargs.get("status", "SENT"),
                **{k: v for k, v in kwargs.items() if k != "status"},
            }
            self._mem.inquiries[inq_id] = record
            return record

    # ------------------------------------------------------------------
    # Supplier Response
    # ------------------------------------------------------------------

    def create_response(
        self,
        project_id: str,
        edge_id: str,
        from_actor_id: str,
        to_actor_id: str,
        inquiry_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        if self._mode == "on":
            resp = self._response_repo.create_supplier_response(
                project_id=project_id,
                edge_id=edge_id,
                from_actor_id=from_actor_id,
                to_actor_id=to_actor_id,
                inquiry_id=inquiry_id,
                **kwargs,
            )
            return {
                "response_id": resp.response_id,
                "project_id": resp.project_id,
                "edge_id": resp.edge_id,
                "inquiry_id": resp.inquiry_id,
                "can_supply": resp.can_supply,
            }
        else:
            resp_id = _new_id()
            record = {
                "response_id": resp_id,
                "project_id": project_id,
                "edge_id": edge_id,
                "inquiry_id": inquiry_id,
                "from_actor_id": from_actor_id,
                "to_actor_id": to_actor_id,
                **kwargs,
            }
            self._mem.responses[resp_id] = record
            return record

    # ------------------------------------------------------------------
    # Supplier Response Rollup
    # ------------------------------------------------------------------

    def create_rollup(
        self,
        project_id: str,
        main_supplier_actor_id: str,
        **kwargs: Any,
    ) -> dict:
        if self._mode == "on":
            rollup = self._rollup_repo.create_rollup(
                project_id=project_id,
                main_supplier_actor_id=main_supplier_actor_id,
                **kwargs,
            )
            return {
                "rollup_id": rollup.rollup_id,
                "project_id": rollup.project_id,
                "can_accept_order": rollup.can_accept_order,
            }
        else:
            rollup_id = _new_id()
            record = {
                "rollup_id": rollup_id,
                "project_id": project_id,
                "main_supplier_actor_id": main_supplier_actor_id,
                **kwargs,
            }
            self._mem.rollups[rollup_id] = record
            return record

    # ------------------------------------------------------------------
    # Execution Event
    # ------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        project_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        if self._mode == "on":
            event = self._event_repo.log_event(
                event_type=event_type,
                project_id=project_id,
                **kwargs,
            )
            return {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "project_id": event.project_id,
            }
        else:
            event_id = _new_id()
            record = {
                "event_id": event_id,
                "event_type": event_type,
                "project_id": project_id,
                **kwargs,
            }
            self._mem.events.append(record)
            return record

    # ------------------------------------------------------------------
    # Row counts (used by verifier assertions)
    # ------------------------------------------------------------------

    def get_counts(self) -> Dict[str, int]:
        """Return cumulative row counts for every integration-relevant table."""
        if self._mode == "on":
            from src.db.models.actor import Actor
            from src.db.models.project import Project
            from src.db.models.requirement import StructuredRequirement
            from src.db.models.inquiry import SupplierInquiry
            from src.db.models.response import SupplierResponse
            from src.db.models.rollup import SupplierResponseRollup
            from src.db.models.procurement_edge import ProcurementEdge
            from src.db.models.execution_event import ExecutionEvent

            return {
                "actors": self._session.query(Actor).count(),
                "projects": self._session.query(Project).count(),
                "structured_requirements": self._session.query(
                    StructuredRequirement
                ).count(),
                "supplier_inquiries": self._session.query(SupplierInquiry).count(),
                "supplier_responses": self._session.query(SupplierResponse).count(),
                "supplier_response_rollups": self._session.query(
                    SupplierResponseRollup
                ).count(),
                "procurement_edges": self._session.query(ProcurementEdge).count(),
                "execution_events": self._session.query(ExecutionEvent).count(),
            }
        else:
            return {
                "actors": self._mem.count_actors(),
                "projects": self._mem.count_projects(),
                "structured_requirements": self._mem.count_requirements(),
                "supplier_inquiries": self._mem.count_inquiries(),
                "supplier_responses": self._mem.count_responses(),
                "supplier_response_rollups": self._mem.count_rollups(),
                "procurement_edges": self._mem.count_edges(),
                "execution_events": self._mem.count_events(),
            }

    # ------------------------------------------------------------------
    # Query helpers (used by hardening suite)
    # ------------------------------------------------------------------

    def list_project_responses(self, project_id: str) -> List[dict]:
        """All supplier responses for a project (all revisions included)."""
        if self._mode == "on":
            from src.db.models.response import SupplierResponse

            rows = (
                self._session.query(SupplierResponse)
                .filter(SupplierResponse.project_id == project_id)
                .all()
            )
            return [
                {
                    "response_id": r.response_id,
                    "inquiry_id": r.inquiry_id,
                    "edge_id": r.edge_id,
                    "can_supply": r.can_supply,
                    "price": r.price,
                    "currency": r.currency,
                    "lead_time_days": r.lead_time_days,
                    "risk_flags_json": r.risk_flags_json,
                    "raw_message": r.raw_message,
                }
                for r in rows
            ]
        else:
            return [
                r for r in self._mem.responses.values()
                if r.get("project_id") == project_id
            ]

    def list_inquiry_responses(self, inquiry_id: str) -> List[dict]:
        """All responses linked to a specific inquiry (for revision tracking)."""
        if self._mode == "on":
            from src.db.models.response import SupplierResponse

            rows = (
                self._session.query(SupplierResponse)
                .filter(SupplierResponse.inquiry_id == inquiry_id)
                .all()
            )
            return [
                {
                    "response_id": r.response_id,
                    "inquiry_id": r.inquiry_id,
                    "price": r.price,
                    "lead_time_days": r.lead_time_days,
                    "raw_message": r.raw_message,
                }
                for r in rows
            ]
        else:
            return [
                r for r in self._mem.responses.values()
                if r.get("inquiry_id") == inquiry_id
            ]

    def list_project_events(self, project_id: str) -> List[dict]:
        """All execution events for a project in chronological order."""
        if self._mode == "on":
            from src.db.models.execution_event import ExecutionEvent

            rows = (
                self._session.query(ExecutionEvent)
                .filter(ExecutionEvent.project_id == project_id)
                .order_by(ExecutionEvent.created_at)
                .all()
            )
            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "project_id": e.project_id,
                    "actor_id": e.actor_id,
                    "edge_id": e.edge_id,
                    "payload_json": e.payload_json,
                }
                for e in rows
            ]
        else:
            return [
                e for e in self._mem.events
                if e.get("project_id") == project_id
            ]

    def list_project_inquiries(self, project_id: str) -> List[dict]:
        """All supplier inquiries for a project."""
        if self._mode == "on":
            from src.db.models.inquiry import SupplierInquiry

            rows = (
                self._session.query(SupplierInquiry)
                .filter(SupplierInquiry.project_id == project_id)
                .all()
            )
            return [
                {
                    "inquiry_id": i.inquiry_id,
                    "edge_id": i.edge_id,
                    "from_actor_id": i.from_actor_id,
                    "to_actor_id": i.to_actor_id,
                    "status": i.status,
                }
                for i in rows
            ]
        else:
            return [
                i for i in self._mem.inquiries.values()
                if i.get("project_id") == project_id
            ]

    def list_project_edges(self, project_id: str) -> List[dict]:
        """All procurement edges for a project."""
        if self._mode == "on":
            edges = self._graph_repo.get_project_edges(project_id)
            return [
                {
                    "edge_id": e.edge_id,
                    "edge_type": e.edge_type,
                    "inquiry_id": e.inquiry_id,
                    "response_id": e.response_id,
                    "status": e.status,
                }
                for e in edges
            ]
        else:
            return [
                e for e in self._mem.edges.values()
                if e.get("project_id") == project_id
            ]

    def check_graph_consistency(self, project_id: str) -> List[str]:
        """Return a list of consistency issues for *project_id*.

        Empty list means the procurement graph is consistent.

        Checks:
          - Every supplier_inquiry.edge_id exists in procurement_edges.
          - Every supplier_response.inquiry_id exists in supplier_inquiries.
          - Every APPROVED / RESPONDED edge has inquiry_id set.
          - Every APPROVED edge has response_id set.
        """
        issues: List[str] = []

        inquiries = self.list_project_inquiries(project_id)
        responses = self.list_project_responses(project_id)
        edges = self.list_project_edges(project_id)

        edge_ids = {e["edge_id"] for e in edges}
        inquiry_ids = {i["inquiry_id"] for i in inquiries}

        for inq in inquiries:
            if inq["edge_id"] not in edge_ids:
                issues.append(
                    f"inquiry {inq['inquiry_id'][:8]} references missing edge "
                    f"{inq['edge_id'][:8]}"
                )

        for resp in responses:
            if resp.get("inquiry_id") and resp["inquiry_id"] not in inquiry_ids:
                issues.append(
                    f"response {resp['response_id'][:8]} references missing inquiry "
                    f"{resp['inquiry_id'][:8]}"
                )

        for edge in edges:
            if edge["status"] in ("SENT", "RESPONDED", "APPROVED"):
                if not edge.get("inquiry_id"):
                    issues.append(
                        f"edge {edge['edge_id'][:8]} status={edge['status']} "
                        f"but inquiry_id is unset"
                    )
            if edge["status"] == "APPROVED":
                if not edge.get("response_id"):
                    issues.append(
                        f"edge {edge['edge_id'][:8]} status=APPROVED "
                        f"but response_id is unset"
                    )

        return issues

    # ------------------------------------------------------------------
    # DB health checks (on-mode only; noop in off-mode)
    # ------------------------------------------------------------------

    def check_integrity(self) -> str:
        """PRAGMA integrity_check — returns 'ok' on a clean database."""
        if self._mode != "on":
            return "ok"
        from sqlalchemy import text

        row = self._session.execute(text("PRAGMA integrity_check")).fetchone()
        return row[0] if row else "unknown"

    def check_foreign_keys(self) -> List[Any]:
        """PRAGMA foreign_key_check — returns [] when there are no violations."""
        if self._mode != "on":
            return []
        from sqlalchemy import text

        return self._session.execute(text("PRAGMA foreign_key_check")).fetchall()
