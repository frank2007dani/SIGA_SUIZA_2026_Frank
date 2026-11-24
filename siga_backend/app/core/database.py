from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
from app.core.config import settings
import ssl
from urllib.parse import parse_qs, urlparse

# Metadata para el Core (solo identidad)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
_SSL_EXEMPT_HOSTS = ("localhost", "127.0.0.1", "::1", "host.docker.internal", "postgres")
_parsed_db_url = urlparse(settings.DATABASE_URL or "")
_db_host = _parsed_db_url.hostname or settings.DB_HOST
_db_sslmode = parse_qs(_parsed_db_url.query).get("sslmode", [None])[0]
connect_args = {}
if _db_host not in _SSL_EXEMPT_HOSTS and not _db_sslmode:
    connect_args["ssl"] = _ssl_ctx

# Engine asíncrono para el Core
engine = create_async_engine(settings.database_url, echo=settings.debug, connect_args=connect_args)

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