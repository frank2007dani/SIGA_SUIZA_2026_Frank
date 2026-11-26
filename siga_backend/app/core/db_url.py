import os
import ssl
from functools import lru_cache
from typing import Optional

from sqlalchemy.engine import URL, make_url

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal", "postgres", "siga-core"}


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
