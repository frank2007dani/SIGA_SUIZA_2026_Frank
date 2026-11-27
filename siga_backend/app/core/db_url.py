import os
import ssl
from functools import lru_cache
from typing import Optional

from sqlalchemy.engine import URL, make_url

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal", "postgres", "siga-core"}
_ENGINE_REGISTRY = []


def is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


@lru_cache(maxsize=1)
def render_internal_tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _render(url: URL) -> str:
    return url.render_as_string(hide_password=False)


def _as_async_url(url: str) -> URL:
    parsed = make_url(url)
    query = dict(parsed.query)
    query.pop("sslmode", None)
    return parsed.set(drivername="postgresql+asyncpg").set(query=tuple(query.items()))


def _as_sync_url(url: str) -> URL:
    parsed = make_url(url)
    return parsed.set(drivername="postgresql+psycopg")


def build_async_database_url(
    url: Optional[str] = None,
    *,
    user: str = "postgres",
    password: Optional[str] = None,
    host: str = "localhost",
    port: str = "5432",
    database: str = "siga_suiza_2026",
) -> str:
    if url:
        return _render(_as_async_url(url))
    parsed = URL.create(
        drivername="postgresql+asyncpg",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )
    return _render(parsed)


def build_sync_database_url(
    url: Optional[str] = None,
    *,
    user: str = "postgres",
    password: Optional[str] = None,
    host: str = "localhost",
    port: str = "5432",
    database: str = "siga_suiza_2026",
) -> str:
    if url:
        return _render(_as_sync_url(url))
    parsed = URL.create(
        drivername="postgresql+psycopg",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )
    return _render(parsed)


def _database_source(url: Optional[str] = None) -> Optional[str]:
    return url or os.getenv("DATABASE_URL") or os.getenv("DB_URL")


def async_connect_args(url: Optional[str] = None) -> dict:
    source = _database_source(url)
    parsed = make_url(source) if source else None
    url_mode = parsed.query.get("sslmode") if parsed else None
    env_mode = os.getenv("DB_SSLMODE")
    mode = url_mode or env_mode
    mode = str(mode).strip().lower() if mode else None
    host = (parsed.host if parsed and parsed.host else os.getenv("DB_HOST", "localhost")).strip().lower()

    if mode == "disable":
        return {"ssl": False}
    if mode in {"require", "verify-ca", "verify-full"}:
        if is_production():
            return {"ssl": render_internal_tls_context()}
        return {"ssl": True}
    if mode in {"allow", "prefer"} or not mode:
        if is_production() and host not in _LOCAL_HOSTS:
            return {"ssl": render_internal_tls_context()}
        return {}
    return {}


def env_database_url() -> str:
    return build_async_database_url(
        os.getenv("DATABASE_URL") or os.getenv("DB_URL"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "siga_suiza_2026"),
    )


def async_engine_kwargs(url: Optional[str] = None, poolclass=None, echo: Optional[bool] = None) -> dict:
    options = {
        "echo": not is_production() if echo is None else echo,
        "connect_args": async_connect_args(url),
    }
    if poolclass is not None:
        options["poolclass"] = poolclass
        return options
    options.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "2")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "3")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "10")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "180")),
        pool_pre_ping=True,
    )
    return options


def register_engine(engine):
    if all(registered is not engine for registered in _ENGINE_REGISTRY):
        _ENGINE_REGISTRY.append(engine)
    return engine


async def dispose_all_engines():
    for engine in list(_ENGINE_REGISTRY):
        await engine.dispose()
