"""API v1 router registry — convention-based auto-discovery.

Every module in :mod:`app.api.v1.routers` that exposes a ``router`` attribute
is mounted automatically under ``/api/v1``. This keeps domain development
additive: dropping in a new ``routers/<domain>.py`` file registers its
endpoints without touching this registry, and the OpenAPI schema is always in
sync with the code that actually exists.
"""

from importlib import import_module
from typing import Any

from fastapi import APIRouter

_ROUTERS_PKG = "app.api.v1.routers"

api_router = APIRouter(
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient role"},
    }
)


def discover_routers() -> list[tuple[str, Any]]:
    """Import every routers module that carries a ``router`` attribute."""
    import pkgutil

    package = import_module(_ROUTERS_PKG)
    found: list[tuple[str, Any]] = []
    for module_info in sorted(pkgutil.iter_modules(package.__path__), key=lambda m: m.name):
        if module_info.name.startswith("_"):
            continue
        module = import_module(f"{_ROUTERS_PKG}.{module_info.name}")
        router = getattr(module, "router", None)
        if router is not None:
            found.append((module_info.name, router))
    return found


for _name, _router in discover_routers():
    api_router.include_router(_router)
