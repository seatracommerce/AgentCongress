from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


# asyncpg does not accept sslmode/channel_binding in connect(); use ssl=True in connect_args instead
_ASYNCPG_DROP_QUERY_KEYS = frozenset({"sslmode", "channel_binding"})


def _make_engine():
    settings = get_settings()
    url = settings.database_url
    # Neon and others often give postgresql://; we need asyncpg for create_async_engine
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = "postgresql+asyncpg://" + url.split("://", 1)[1]
    kwargs: dict = {"pool_pre_ping": True}
    if not url.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    # Strip sslmode/channel_binding from URL and pass ssl to asyncpg via connect_args
    if "asyncpg" in url:
        parsed = urlparse(url)
        if parsed.query:
            pairs = parse_qsl(parsed.query, keep_blank_values=True)
            need_ssl = any(k.lower() in _ASYNCPG_DROP_QUERY_KEYS for k, _ in pairs)
            qs = [(k, v) for k, v in pairs if k.lower() not in _ASYNCPG_DROP_QUERY_KEYS]
            new_query = urlencode(qs)
            url = urlunparse(parsed._replace(query=new_query))
            if need_ssl:
                kwargs["connect_args"] = kwargs.get("connect_args", {}) | {"ssl": True}
    return create_async_engine(url, **kwargs)


engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
