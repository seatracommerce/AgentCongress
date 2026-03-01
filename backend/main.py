from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.bills import router as bills_router
from backend.api.debates import router as debates_router
from backend.api.admin import router as admin_router
from backend.api.stats import router as stats_router
from backend.scheduler.tasks import start_scheduler, shutdown_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.config import get_settings
    logger.info("Starting AgentCongress API")
    if not get_settings().disable_scheduler:
        start_scheduler()
    else:
        logger.info("In-process scheduler disabled (use Cloud Scheduler + POST /admin/trigger-poll)")
    yield
    logger.info("Shutting down AgentCongress API")
    await shutdown_scheduler()


app = FastAPI(
    title="AgentCongress API",
    description="Multi-agent congressional debate simulator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bills_router, prefix="/bills", tags=["bills"])
app.include_router(debates_router, prefix="/debates", tags=["debates"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(stats_router, prefix="/stats", tags=["stats"])


@app.get("/health")
async def health_check():
    """Liveness: app is running. No dependency checks."""
    return {"status": "ok"}


@app.get("/ready")
async def ready_check():
    """Readiness: app can serve traffic. Checks DB connectivity (e.g. Neon)."""
    from sqlalchemy import text
    from backend.database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "checks": {"database": "ok"}}
    except Exception as e:
        logger.exception("Ready check failed")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "error", "checks": {"database": "fail"}, "detail": str(e)},
        )
