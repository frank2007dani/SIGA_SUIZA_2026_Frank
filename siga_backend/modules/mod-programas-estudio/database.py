from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
from sqlalchemy.pool import NullPool
import os
import sys
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, JSON, Boolean

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
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

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class TimeStampedMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BaseModel(Base, TimeStampedMixin):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)

class OutboxEvent(BaseModel):
    __tablename__ = "outbox_events"
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    published = Column(Boolean, default=False, index=True)

_is_test = (os.getenv("DB_NAME") == "siga_test") or ("pytest" in sys.modules)

if _is_test:
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool, connect_args=_connect_args)
else:
    engine = create_async_engine(
        DATABASE_URL, 
        echo=False, 
        connect_args=_connect_args,
        pool_size=10, 
        max_overflow=20, 
        pool_pre_ping=True, 
        pool_recycle=300
    )
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except BaseException:
            await db.rollback()
            raise
        finally:
            await db.close()

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        print("Tablas creadas/verificadas")
    except Exception as e:
        print(f"init_db: tablas ya existen o error menor: {e}")