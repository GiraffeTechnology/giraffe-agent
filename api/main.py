from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.health import router as health_router
from api.routes.auth import router as auth_router
from api.routes.participants import router as participants_router
from api.routes.projects import router as projects_router
from api.routes.dynamic_forms import router as dynamic_forms_router
from api.routes.approval_gates import router as approval_gates_router
from api.routes.matching import router as matching_router
from api.routes.rfq import router as rfq_router
from api.routes.supplier_responses import router as supplier_responses_router
from api.routes.decision_packets import router as decision_packets_router
from api.routes.orders import router as orders_router

app = FastAPI(
    title="Giraffe Agent v1.0 — Apparel & Textile Industry Edition",
    version="1.0.0",
    description="Production-usable C2M apparel & textile order execution platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(participants_router, prefix="/api/participants", tags=["participants"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(dynamic_forms_router, prefix="/api", tags=["dynamic_forms"])
app.include_router(approval_gates_router, prefix="/api", tags=["approval_gates"])
app.include_router(matching_router, prefix="/api", tags=["matching"])
app.include_router(rfq_router, prefix="/api", tags=["rfq"])
app.include_router(supplier_responses_router, prefix="/api", tags=["supplier_responses"])
app.include_router(decision_packets_router, prefix="/api", tags=["decision_packets"])
app.include_router(orders_router, prefix="/api", tags=["orders"])
