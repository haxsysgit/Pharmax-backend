# Backend Project Structure

This backend is organized as a small-but-professional FastAPI project with a clear separation between:

- **Application code** (`app/`)
- **Runtime data** (SQLite database file in `app/_db/`)
- **Tests** (`tests/`)

## Directory Tree

```text
Backend/
  app/
    __init__.py
    main.py

    _db/
      vigilis.db            # generated at runtime (ignored by git)

    api/
      __init__.py
      router.py

      routes/
        __init__.py
        auth.py
        users.py
        items.py

    core/
      __init__.py
      config.py
      security.py
      dependencies.py

    db/
      __init__.py
      base.py
      session.py

    services/
      __init__.py
      user_service.py

    models/
      __init__.py
      product.py
      stock_adjustment.py

    schemas/
      __init__.py

  tests/
    __init__.py

  main.py                 # entrypoint (re-exports `app` from app.main)
```

## What each folder/file does

### `Backend/app/`
- **Purpose**: all backend source code lives here.

### `Backend/app/main.py`
- **Purpose**: defines the FastAPI `app`, registers routers, and initializes the DB on startup.

### `Backend/app/api/router.py`
- **Purpose**: the central router that includes all route modules.
- Add new route modules in `app/api/routes/` and include them here.

### `Backend/app/api/routes/`
- **Purpose**: FastAPI route handlers grouped by feature.

### `Backend/app/models/`
- **Purpose**: SQLAlchemy ORM models (tables).
- Current models:
  - `Product`
  - `StockAdjustment`

### `Backend/app/schemas/`
- **Purpose**: Pydantic schemas (request/response models).
- This keeps API contracts separate from database models.

### `Backend/app/db/`
- **Purpose**: database plumbing.
- `base.py`: defines SQLAlchemy `Base`.
- `session.py`: engine + session factory + `get_db()` dependency + `init_db()`.

### `Backend/app/_db/`
- **Purpose**: runtime database files.
- `vigilis.db` will be created here automatically when you start the app.

### `Backend/tests/`
- **Purpose**: backend tests (pytest, etc.).

## How to run the backend (current workflow)

From inside the `Backend/` directory:

```bash
uv run fastapi dev main.py
```

- App will start and create the SQLite DB at:
  - `Backend/app/_db/vigilis.db`

## Next step (after structure): Alembic migrations

Once you confirm this structure runs, the next step is to initialize Alembic inside `Backend/` and have it track `Base.metadata` from `app.db.base`.
