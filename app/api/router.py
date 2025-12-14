from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.items import router as items_router
from app.api.routes.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(items_router, prefix="/items", tags=["items"])
