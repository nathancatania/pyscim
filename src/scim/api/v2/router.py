from fastapi import APIRouter
from .users import router as users_router
from .groups import router as groups_router
from .service_provider_config import router as sp_config_router
from .schemas import router as schemas_router
from .resource_types import router as resource_types_router

# Create the main v2 router
router = APIRouter(prefix="/scim/v2")

# Include all sub-routers
router.include_router(users_router)
router.include_router(groups_router)
router.include_router(sp_config_router)
router.include_router(schemas_router)
router.include_router(resource_types_router)