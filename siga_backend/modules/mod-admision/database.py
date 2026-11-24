from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import os

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "siga_suiza_2026")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    host = (parsed.hostname or "").lower()
    connect_args = {}
    if host not in _SSL_EXEMPT_HOSTS and sslmode != "disable":
        connect_args["ssl"] = True
    return clean_url, connect_args

DATABASE_URL, _connect_args = _normalizar_database_url_asyncpg(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
