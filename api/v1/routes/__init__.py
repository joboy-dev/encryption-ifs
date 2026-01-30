from fastapi import APIRouter

from api.v1.routes.index import index_router
from api.v1.routes.errors import error_router

v1_router = APIRouter()

# Register all routes
v1_router.include_router(index_router)
v1_router.include_router(error_router)
