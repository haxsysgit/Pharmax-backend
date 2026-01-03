from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.admin import setup_admin
from app.core.config import CORS_ORIGINS, SECRET_KEY
from app.api.router import api_router
from app.db.session import init_db


app = FastAPI(title="Vigilis Pharmacy Backend", version="1.0.0")


@app.get("/")
def get_root():
    return {
        "status": "success",
        "pharmacy": "Vigilis Pharmacy",
        "version": "1.0.0",
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
)

@app.on_event("startup")
def _startup():
    init_db()
    setup_admin(app, secret_key=SECRET_KEY)


app.include_router(api_router)
