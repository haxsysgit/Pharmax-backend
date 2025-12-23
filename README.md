# Pharmax Backend API

Backend for the **Pharmax** system, built with **FastAPI + SQLAlchemy + Alembic**.

This README documents:

- **How to run** the backend locally
- **Database & migrations**
- **API overview**
- **Detailed route documentation** for the implemented modules:
  - Root & health
  - Products & stock adjustments
  - Product units
  - Invoices
  - Auth & Users (current placeholders)

---

## 1. Tech Stack & Project Layout

- **Framework**: FastAPI
- **ORM**: SQLAlchemy (declarative models)
- **DB**: SQLite (single-file DB, good for local/dev)
- **Migrations**: Alembic
- **Validation / Schemas**: Pydantic v2
- **Dev runner**: [`uv`](https://github.com/astral-sh/uv) + `fastapi` CLI

Key backend paths (relative to `/Backend`):

- App code: `app/`
  - Entry: `app/main.py`
  - API router aggregator: `app/api/router.py`
  - API route modules: `app/api/routes/*.py`
  - Models: `app/models/*.py`
  - Schemas: `app/schemas/*.py`
  - DB session/config: `app/db/session.py`, `app/core/config.py`
- Alembic migrations: `alembic/versions/*.py`
- Dev scripts: `scripts/`
- Tests: `tests/`

---

## 2. Running the Backend

From the `/Backend` directory:

```bash
# Install dependencies (using uv)
uv sync

# Run FastAPI dev server
uv run fastapi dev main.py
```

By default this starts FastAPI on `http://127.0.0.1:8000` (or `http://localhost:8000`).

### 2.1. Root Health Endpoint

- **Method**: `GET`
- **Path**: `/`
- **Description**: Simple health/status check for the backend.

**Response 200 (example):**

```json
{
  "status": "success",
  "pharmacy": "Vigilis Pharmacy",
  "version": "0.1.0"
}
```

---

## 3. Database & Migrations

### 3.1. Location

Database configuration lives in `app/core/config.py`:

- Base directory: `BASE_DIR = Path(__file__).resolve().parents[2]`
- DB directory: `app/_db/`
- SQLite file: `app/_db/vigilis.db`
- Connection URL: `sqlite:///app/_db/vigilis.db`

`app/db/session.py` defines:

- `engine`
- `SessionLocal`
- `get_db()` – FastAPI dependency for DB sessions
- `init_db()` – imports models so SQLAlchemy metadata is fully registered

`init_db()` is called on FastAPI startup.

### 3.2. Running Migrations (Alembic)

Alembic migration scripts live in:

- `alembic/versions/`

Typical workflow (from `/Backend`):

```bash
# (Example) upgrade to latest
alembic upgrade head

# (Example) downgrade one step
alembic downgrade -1
```

> Note: Exact Alembic CLI usage depends on how you configure `alembic.ini`. Adjust commands if needed.

### 3.3. Seeding & Dev Scripts

In `scripts/`:

- `seed_dev_data.py` – CSV-based / scripted dev data seeding
- `smoke_test_invoices.sh` – helper script to smoke-test invoice flows against the running API

Run them from `/Backend`, for example:

```bash
uv run python scripts/seed_dev_data.py
./scripts/smoke_test_invoices.sh
```

---

## 4. API Overview

All API routers are wired in `app/api/router.py`:

```python
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
```

Effective base paths (relative to `http://localhost:8000`):

- `/` – Root health
- `/auth/...` – Auth-related endpoints (currently a simple `ping`)
- `/users/...` – User-related endpoints (currently a simple `ping`)
- `/products/...` – Product inventory & stock adjustments
- `/invoices/...` – Invoice creation, line items, finalize/cancel, list/read

### 4.1. High-Level Endpoint Summary

| Area        | Method | Path                                  | Description                                   |
|------------|--------|---------------------------------------|-----------------------------------------------|
| Root       | GET    | `/`                                   | Backend health & version info                 |
| Auth       | GET    | `/auth/ping`                          | Simple ping, auth not implemented yet         |
| Users      | GET    | `/users/ping`                         | Simple ping, user system not implemented yet  |
| Products   | POST   | `/products/`                          | Create a new product                          |
| Products   | GET    | `/products/`                          | List products (optional search)               |
| Products   | GET    | `/products/{product_id}`              | Get a single product                          |
| Products   | PATCH  | `/products/{product_id}`              | Partially update a product                    |
| Products   | DELETE | `/products/{product_id}`              | Delete a product                              |
| Units      | GET    | `/products/{product_id}/units`        | List units for a product                      |
| Units      | GET    | `/products/{product_id}/units/{unit_id}` | Get one unit (and validate belongs to product) |
| Stock      | POST   | `/products/{product_id}/adjust-stock` | Adjust stock (audit + new snapshot)          |
| Invoices   | POST   | `/invoices/`                          | Create a new invoice                          |
| Invoices   | POST   | `/invoices/{invoice_id}/items`        | Add line item to invoice                      |
| Invoices   | GET    | `/invoices/all`                       | List invoices (most recent first)             |
| Invoices   | POST   | `/invoices/{invoice_id}/finalize`     | Finalize invoice & deduct stock               |
| Invoices   | POST   | `/invoices/{invoice_id}/cancel`       | Cancel invoice (with stock reversal rules)    |
| Invoices   | GET    | `/invoices/{invoice_id}`              | Read a single invoice                         |

Below are more detailed docs per area.

---

## 5. Products API

Module: `app/api/routes/products_route.py`

### 5.1. Create Product

- **Method**: `POST`
- **Path**: `/products/`
- **Body schema**: `CreateProduct`

```json
{
  "sku": "AMOX-500-CAP",
  "name": "Amoxicillin 500mg Capsules",
  "brand_name": "Some Brand",
  "supplier_name": "Main Supplier",
  "barcode": "1234567890123",
  "markup_percent": 20.0,
  "reorder_level": 10,
  "product_type": "Non-medical",
  "dispense_without_prescription": true,
  "return_policy": "No returns after 7 days",
  "status": "Active"
}
```

**Behavior:**

- Checks if a product with the same `sku` already exists.
  - If yes → **400** `{"detail": "Product already exists"}`
- Otherwise creates the product with:
  - `quantity_on_hand` default `0`
  - Timestamps set by DB.

**Responses:**

- `201` / `200` – `ReadProduct` (includes `id`, `quantity_on_hand`, `created_at`, `updated_at`).

### 5.2. List Products (with Optional Search)

- **Method**: `GET`
- **Path**: `/products/`
- **Query params**:
  - `query: string | null` – optional search term applied to `name` and `brand_name`.

**Examples:**

- `GET /products/` – list all products.
- `GET /products/?query=amox` – filter where `name` or `brand_name` contains `"amox"`.

**Response:**

- `200` – `list[ReadProduct]`.

### 5.3. Get Single Product

- **Method**: `GET`
- **Path**: `/products/{product_id}`
- **Path params**:
  - `product_id: str` (UUID string, matches `Product.id`)

**Response:**

- `200` – `ReadProduct`
- `404` – `{"detail": "Product not found"}`

### 5.4. Update Product (Partial)

- **Method**: `PATCH`
- **Path**: `/products/{product_id}`
- **Body schema**: `UpdateProduct` (all fields optional)

Rules:

- Only fields actually present in the body are updated.
- If body is empty → `400` `{"detail": "No data to update"}`.

**Response:**

- `200` – `ReadProduct` (updated object)
- `404` – `{"detail": "Product not found"}`

### 5.5. Delete Product

- **Method**: `DELETE`
- **Path**: `/products/{product_id}`

**Response:**

- `200` – e.g.

```json
{
  "status": "deleted",
  "message": "Product deleted successfully"
}
```

- `404` – `{"detail": "Product not found"}`

---

## 6. Product Units API

Models: `app/models/product_unit_table.py`, `app/models/product_table.py`

- A `Product` has many `ProductUnit` rows (`product_units` relationship).
- Each `ProductUnit` represents a sale unit (e.g. Pack, Strip, Bottle) with:
  - `name: BaseUnit` (enum of units like `Tablet`, `Capsule`, `Pack`, `Bottle`, etc.)
  - `multiplier_to_base: int` – how many base units this unit represents
  - `price_per_unit: float` – price for one of this unit
  - `is_default: bool` – whether this is the default selling unit

Schema: `ReadProductUnit` in `app/schemas/product_unit_schema.py`.

### 6.1. List Units for a Product

- **Method**: `GET`
- **Path**: `/products/{product_id}/units`

**Response:**

- `200` – `list[ReadProductUnit]`
- If product has no units → returns an empty list.

### 6.2. Get Single Unit for a Product

- **Method**: `GET`
- **Path**: `/products/{product_id}/units/{unit_id}`

**Behavior:**

- Looks up a `ProductUnit` with given `unit_id` and ensures `product_id` matches.
- If not found or doesn’t belong to the product → `404` with message like:
  - `{"detail": "This Unit doesn't belong to this product"}`

**Response:**

- `200` – `ReadProductUnit`

---

## 7. Stock Adjustments API

Schema: `CreateStockAdjustment`, `AdjustStockResponse` in `app/schemas/stock_adjustment_schema.py`.

### 7.1. Adjust Stock for a Product

- **Method**: `POST`
- **Path**: `/products/{product_id}/adjust-stock`
- **Body schema**: `CreateStockAdjustment`

```json
{
  "change_qty": 5,
  "reason": "ManualCorrection",
  "reference": "Initial load",
  "note": "Opening balance adjustment"
}
```

**Behavior:**

- Loads product by `product_id`.
- Computes new `quantity_on_hand = existing + change_qty`.
- Rejects if new quantity would be negative:
  - `400` – `{"detail": "Cannot adjust stock to a negative quantity"}`
- Creates a `StockAdjustment` audit row with:
  - `product_id`
  - `change_qty`
  - `reason`, `reference`, `note`
- Commits product update + adjustment in a single transaction.

**Response:**

- `200` – `AdjustStockResponse`:

```json
{
  "adjustment": {
    "id": "...",
    "product_id": "...",
    "change_qty": 5,
    "reason": "ManualCorrection",
    "reference": "Initial load",
    "note": "Opening balance adjustment",
    "created_at": "2025-01-01T12:00:00Z"
  },
  "product": {
    "id": "...",
    "sku": "AMOX-500-CAP",
    "name": "Amoxicillin 500mg Capsules",
    "quantity_on_hand": 5,
    "...": "other product fields"
  }
}
```

---

## 8. Invoices API

Module: `app/api/routes/invoices_route.py`

Models:

- `Invoice` (`app/models/invoice_table.py`)
- `InvoiceItem` (`app/models/invoice_item_table.py`)

Key enums and statuses:

- `InvoiceStatus` (e.g. `DRAFT`, `FINALIZED`, `CANCELLED`)

Schemas:

- `CreateInvoice`, `ReadInvoice` – `app/schemas/invoice_schema.py`
- `AddInvoiceItem`, `ReadInvoiceItem` – `app/schemas/invoice_item_schema.py`

### 8.1. Create Invoice

- **Method**: `POST`
- **Path**: `/invoices/`
- **Body schema**: `CreateInvoice`

```json
{
  "sold_by_name": "John Doe"
}
```

**Behavior:**

- Creates a new invoice with:
  - `status = DRAFT`
  - Empty `items` list

**Response:**

- `200` – `ReadInvoice` with:
  - `id`, `sold_by_name`, `status`, `created_at`, `items`, `total`

### 8.2. Add Invoice Item

- **Method**: `POST`
- **Path**: `/invoices/{invoice_id}/items`
- **Body schema**: `AddInvoiceItem`

```json
{
  "product_id": "...",
  "product_unit_id": "...",
  "quantity": 2,
  "unit_price": 500.0
}
```

**Behavior:**

- Loads invoice (`DRAFT` only).
- Loads product and unit.
- Validates `unit.product_id == product.id`.
- Uses provided `unit_price` or falls back to `unit.price_per_unit`.
- Computes `line_total = quantity * unit_price`.
- Appends `InvoiceItem` to invoice and commits.

**Response:**

- `200` – updated `ReadInvoice` with items and `total`.
- `400` – various validation errors:
  - Invoice not `DRAFT`
  - Unit doesn’t belong to product
  - Unit price <= 0

### 8.3. List Invoices

- **Method**: `GET`
- **Path**: `/invoices/all`

**Behavior:**

- Fetches all invoices ordered by `created_at` (desc).

**Response:**

- `200` – `list[ReadInvoice]`

### 8.4. Finalize Invoice

- **Method**: `POST`
- **Path**: `/invoices/{invoice_id}/finalize`

**Behavior:**

- Only `DRAFT` invoices can be finalized.
- Requires at least one line item, otherwise:
  - `400` – `{"detail": "Invoice has no items"}`
- For each item:
  - Ensures `unit.product_id == product.id`.
  - Computes `base_qty = quantity * unit.multiplier_to_base`.
  - Ensures `product.quantity_on_hand >= base_qty`, otherwise:
    - `400` – `{"detail": "Not enough stock"}`
  - Deducts stock in memory.
- Sets `status = FINALIZED`, commits invoice + stock changes.

**Response:**

- `200` – `ReadInvoice` with final `status` and unchanged `total`.

### 8.5. Cancel Invoice

- **Method**: `POST`
- **Path**: `/invoices/{invoice_id}/cancel`

**Behavior:**

- If already `CANCELLED` → `400` – `{"detail": "Invoice is already cancelled"}`.
- If `FINALIZED`:
  - Loops through items and **reverses** stock deduction:
    - `base_qty = quantity * unit.multiplier_to_base`
    - Adds `base_qty` back to `product.quantity_on_hand`.
- If neither `DRAFT` nor `FINALIZED` (unexpected) → `400`.
- If `DRAFT`:
  - No stock movement yet; invoice items are just cleared.
- Sets `status = CANCELLED`, commits.

**Response:**

- `200` – `ReadInvoice` with `status = CANCELLED`.

### 8.6. Read Single Invoice

- **Method**: `GET`
- **Path**: `/invoices/{invoice_id}`

**Response:**

- `200` – `ReadInvoice`
- `404` – `{"detail": "Invoice not found"}`

---

## 9. Auth & Users (Placeholders for Now)

Modules:

- `app/api/routes/auth_route.py`
- `app/api/routes/users_route.py`

Current behavior:

- **Auth ping**
  - Method: `GET`
  - Path: `/auth/ping`
  - Response: `{"status": "ok"}`

- **Users ping**
  - Method: `GET`
  - Path: `/users/ping`
  - Response: `{"status": "ok"}`

There is **no real authentication or user management yet**. These are placeholders for future phases (e.g. JWT, roles like ADMIN/CASHIER/STAFF).

---

## 10. Testing

Tests live under `tests/`.

From `/Backend`, you can run tests with `pytest` (optionally via `uv`):

```bash
uv run pytest
```

Particularly important integration tests:

- `tests/test_invoices_flow.py` – exercises a realistic invoice creation + finalize/cancel flow against the API.

---

## 11. Next Steps & Extensibility

Planned directions for this backend:

- Implement **user accounts** and **authentication** (JWT / session-based) with roles.
- Protect routes with dependencies like `get_current_user` and role checks.
- Add more inventory features (e.g. purchase orders, suppliers, automatic re‑order suggestions).
- Add reporting endpoints (daily sales, stock levels, debtor tracking).

This README should give you (and future you) a clear map of the backend API as it exists now, and a solid base to continue building the Vigilis Pharmacy platform.
