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
    logger.info("Starting AgentCongress API")
    start_scheduler()
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
    return {"status": "ok"}
