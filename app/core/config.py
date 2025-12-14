from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_DIR = BASE_DIR / "app" / "_db"
DB_PATH = DB_DIR / "vigilis.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"
