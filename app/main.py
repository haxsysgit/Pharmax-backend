from fastapi import FastAPI

from app.api.router import api_router
from app.db.session import init_db

app = FastAPI(title="Vigilis Pharmacy Backend", version="0.1.0")


@app.get("/")
def get_root():
    return {
        "status": "success",
        "pharmacy": "Vigilis Pharmacy",
        "version": "0.1.0",
    }


@app.on_event("startup")
def _startup():
    init_db()


app.include_router(api_router)
