import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_DIR = BASE_DIR / "app" / "_db"
DB_PATH = DB_DIR / "vigilis.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

SECRET_KEY = os.getenv("VIGILIS_SECRET_KEY", "vigilis pharmacy")
ALGORITHM = os.getenv("VIGILIS_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("VIGILIS_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

_cors_origins_raw = os.getenv(
    "VIGILIS_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:5174",
)
CORS_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
