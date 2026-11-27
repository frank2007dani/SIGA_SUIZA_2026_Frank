from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
from app.core.config import settings
from app.core.db_url import async_engine_kwargs, register_engine

metadata = MetaData()
Base = declarative_base(metadata=metadata)

engine = register_engine(
    create_async_engine(
        settings.database_url,
        **async_engine_kwargs(echo=settings.effective_debug),
    )
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
        except BaseException:
            await session.rollback()
            raise
        finally:
            await session.close()
