from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base  # 👈 AGREGAR declarative_base aquí
from sqlalchemy import MetaData
from ..config import settings
from ..db_url import async_engine_kwargs, register_engine

# Metadata específica para Identity (separada del Core)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

engine = register_engine(
    create_async_engine(
        settings.database_url,
        **async_engine_kwargs(echo=settings.effective_debug),
    )
)

# Session local para Identity
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_identity_db():
    """Dependencia de base de datos para Identity"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
        finally:
            await session.close()
