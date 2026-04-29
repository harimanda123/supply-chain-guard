from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.database import init_db
from src.api.disruptions import router as disruptions_router
from src.api.carriers import router as carriers_router
from src.api.financials import router as financials_router
from src.api.inventory import router as inventory_router
from src.api.approvals import router as approvals_router
from src.api.pipeline import router as pipeline_router

settings = get_settings()

# ── LangSmith tracing ─────────────────────────────────────────────────────────
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Supply Chain Guard",
    description="Autonomous supply chain disruption detection and recovery engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — restrict to declared origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js demo
        "http://localhost:8000",   # self (Swagger UI)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(disruptions_router)
app.include_router(carriers_router)
app.include_router(financials_router)
app.include_router(inventory_router)
app.include_router(approvals_router)
app.include_router(pipeline_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
