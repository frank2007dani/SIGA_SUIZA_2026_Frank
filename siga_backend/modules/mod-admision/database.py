from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from app.core.db_url import async_engine_kwargs, env_database_url, register_engine

DATABASE_URL = env_database_url()

engine = register_engine(create_async_engine(DATABASE_URL, **async_engine_kwargs(echo=False)))
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
