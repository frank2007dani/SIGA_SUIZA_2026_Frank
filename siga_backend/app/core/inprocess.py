from pathlib import Path
import importlib.util
import logging
import os
import sys
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_MODULE_FOLDERS = {
    "mod-usuarios": "mod-usuarios",
    "mod-planes-estudio": "mod-planes-estudio",
    "mod-programas-estudio": "mod-programas-estudio",
    "mod-gestion-academica": "mod-gestion-academica",
    "mod-auditoria": "mod-auditoria",
    "mod-evaluacion": "mod-evaluacion",
    "mod-admision": "mod-admision",
}

_APPS: Dict[str, Any] = {}
_LIFESPANS: Dict[str, Any] = {}
_LOADED = False
_STARTED = False


def enabled() -> bool:
    return os.getenv("SIGA_SINGLE_PROCESS", "false").strip().lower() in {"1", "true", "yes", "on"}


def _local_names(module_dir: Path) -> set:
    return {path.stem for path in module_dir.glob("*.py") if path.name != "__init__.py"}


def load() -> None:
    global _LOADED
    if _LOADED or not enabled():
        return

    modules_root = Path(__file__).resolve().parents[2] / "modules"
    for name, folder in _MODULE_FOLDERS.items():
        module_dir = modules_root / folder
        main_path = module_dir / "main.py"
        if not main_path.exists():
            logger.warning("No se encontró %s; módulo %s no se cargó en proceso único", main_path, name)
            continue

        local_names = _local_names(module_dir)
        for local_name in local_names:
            sys.modules.pop(local_name, None)

        saved_path = list(sys.path)
        spec_name = f"_siga_inprocess_{folder.replace('-', '_')}"
        sys.path.insert(0, str(module_dir))
        spec = importlib.util.spec_from_file_location(spec_name, main_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"No se pudo cargar {main_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(spec_name, None)
            sys.path[:] = saved_path
            for local_name in local_names:
                sys.modules.pop(local_name, None)

        app = getattr(module, "app", None)
        if app is None:
            raise RuntimeError(f"{main_path} no expone app ASGI")
        _APPS[name] = app
        logger.info("Módulo %s cargado en proceso único", name)

    _LOADED = True


async def start() -> None:
    global _STARTED
    if _STARTED or not enabled():
        return

    load()
    try:
        for name, app in _APPS.items():
            context = app.router.lifespan_context(app)
            await context.__aenter__()
            _LIFESPANS[name] = context
        _STARTED = True
    except Exception:
        await shutdown()
        raise


async def shutdown() -> None:
    global _STARTED
    for name, context in reversed(list(_LIFESPANS.items())):
        try:
            await context.__aexit__(None, None, None)
        except Exception:
            logger.exception("Error al cerrar el ciclo de vida del módulo %s", name)
    _LIFESPANS.clear()
    _STARTED = False


def get_transport(module_name: str) -> Optional[httpx.AsyncBaseTransport]:
    if not enabled():
        return None
    app = _APPS.get(module_name)
    if app is None:
        return None
    return httpx.ASGITransport(app=app, raise_app_exceptions=False)
