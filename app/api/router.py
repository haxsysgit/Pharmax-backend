from fastapi import APIRouter

from app.api.routes.auth_route import router as auth_router
from app.api.routes.products_route import router as products_router
from app.api.routes.users_route import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
