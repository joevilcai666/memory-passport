"""v1 API — business routers mounted under /v1.

Each module owns one resource's routes. The aggregator below composes them into
a single ``router`` that ``app.main`` includes alongside the health router.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.agents import router as agents_router
from app.api.v1.apps import router as apps_router
from app.api.v1.debug import router as debug_router
from app.api.v1.devices import router as devices_router
from app.api.v1.events import router as events_router
from app.api.v1.memories import router as memories_router
from app.api.v1.policies import router as policies_router
from app.api.v1.relationships import router as relationships_router
from app.api.v1.users import router as users_router

router = APIRouter()
router.include_router(apps_router)
router.include_router(agents_router)
router.include_router(users_router)
router.include_router(relationships_router)
router.include_router(devices_router)
router.include_router(events_router)
router.include_router(memories_router)
router.include_router(policies_router)
router.include_router(debug_router)

__all__ = ["router"]
