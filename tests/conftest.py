"""Shared pytest fixtures.

Uses SQLite in-memory (fresh DB per test) so no Postgres is required.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set env vars BEFORE any backend imports so config/database pick them up
os.environ["ENV"] = "test"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["CONGRESS_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DRY_RUN"] = "true"
os.environ["WEBAPP_URL"] = "http://localhost:3000"

from backend.database import Base, get_db
from backend.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(loop_scope="function")
async def engine():
    """Fresh in-memory SQLite DB per test — guarantees isolation."""
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client wired to the per-test SQLite DB."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
