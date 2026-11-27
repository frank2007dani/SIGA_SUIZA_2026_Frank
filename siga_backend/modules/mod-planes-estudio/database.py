from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
from datetime import datetime

from app.core.db_url import async_engine_kwargs, env_database_url, register_engine
from sqlalchemy import Column, Integer, DateTime, String, JSON, Boolean

DATABASE_URL = env_database_url()

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

engine = register_engine(create_async_engine(DATABASE_URL, **async_engine_kwargs()))
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
