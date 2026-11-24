from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
from app.core.config import settings
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Metadata para el Core (solo identidad)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

_SSL_EXEMPT_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal", "postgres"}


def _normalizar_database_url_asyncpg(database_url: str):
    url = database_url or ""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlsplit(url)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    sslmode = None
    filtered_query = []
    for key, value in query_items:
        if key.lower() == "sslmode":
            sslmode = value.lower()
        else:
            filtered_query.append((key, value))

    clean_url = urlunsplit(parsed._replace(query=urlencode(filtered_query, doseq=True)))
    host = (parsed.hostname or settings.DB_HOST or "").lower()
    connect_args = {}
    if host not in _SSL_EXEMPT_HOSTS and sslmode != "disable":
        connect_args["ssl"] = "require"
    return clean_url, connect_args


_DATABASE_URL, _connect_args = _normalizar_database_url_asyncpg(settings.database_url)

# Engine asíncrono para el Core
engine = create_async_engine(
    _DATABASE_URL,
    echo=settings.debug,
    connect_args=_connect_args,
)

# Session local asíncrona
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Dependencia de base de datos para el Core"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()