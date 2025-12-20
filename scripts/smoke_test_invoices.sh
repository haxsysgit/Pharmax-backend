#!/usr/bin/env bash
set -euo pipefail

# Smoke test for invoices routes.
# - auto-picks one product + unit from local SQLite DB
# - creates 2 invoices (1 item and 3 items)
# - lists invoices

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DB_PATH="${BACKEND_DIR}/app/_db/vigilis.db"

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
CURL_TIMEOUT="${CURL_TIMEOUT:-5}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_cmd sqlite3
require_cmd curl
require_cmd python

if [[ ! -f "$DB_PATH" ]]; then
  echo "Database not found at: $DB_PATH" >&2
  echo "Expected DB at Backend/app/_db/vigilis.db" >&2
  exit 1
fi

# Verify API is up (avoid hanging forever)
if ! curl -sS --max-time "$CURL_TIMEOUT" "$BASE_URL/openapi.json" >/dev/null; then
  echo "API is not reachable at $BASE_URL" >&2
  echo "Start it from Backend/: uv run fastapi dev main.py" >&2
  exit 1
fi

# Pick a product + unit pair. Prefer non-zero price to avoid unit_price validation failure.
read -r PRODUCT_ID UNIT_ID UNIT_PRICE < <(
  sqlite3 -separator ' ' "$DB_PATH" "
    SELECT p.id, pu.id,
           COALESCE(NULLIF(pu.price_per_unit, 0), 100.0) AS effective_price
    FROM products p
    JOIN product_units pu ON pu.product_id = p.id
    ORDER BY pu.price_per_unit DESC
    LIMIT 1;
  "
)

if [[ -z "${PRODUCT_ID:-}" || -z "${UNIT_ID:-}" ]]; then
  echo "Could not find product/product_unit rows in DB (are you seeded?)" >&2
  exit 1
fi

# Helper to POST JSON and print response
post_json() {
  local url="$1"
  local data="$2"
  curl -sS --max-time "$CURL_TIMEOUT" -X POST "$url" \
    -H 'Content-Type: application/json' \
    -d "$data"
}

echo "Using BASE_URL: $BASE_URL"
echo "Using DB_PATH:  $DB_PATH"
echo "Picked PRODUCT_ID=$PRODUCT_ID"
echo "Picked UNIT_ID=$UNIT_ID"
echo "Picked UNIT_PRICE=$UNIT_PRICE"
echo

# Create invoice 1
INV1_JSON=$(post_json "$BASE_URL/invoices/" '{"sold_by_name":"Smoke Cashier A"}')
INV1_ID=$(python -c 'import sys,json; print(json.loads(sys.argv[1])["id"])' "$INV1_JSON")
echo "Created invoice 1: $INV1_ID"

# Add 1 item to invoice 1 (override unit_price to be safe)
post_json "$BASE_URL/invoices/${INV1_ID}/items" "{\"product_id\":\"$PRODUCT_ID\",\"product_unit_id\":\"$UNIT_ID\",\"quantity\":1,\"unit_price\":$UNIT_PRICE}" >/dev/null
echo "Added 1 item to invoice 1"

# Create invoice 2
INV2_JSON=$(post_json "$BASE_URL/invoices/" '{"sold_by_name":"Smoke Cashier B"}')
INV2_ID=$(python -c 'import sys,json; print(json.loads(sys.argv[1])["id"])' "$INV2_JSON")
echo "Created invoice 2: $INV2_ID"

# Add 3 items to invoice 2
post_json "$BASE_URL/invoices/${INV2_ID}/items" "{\"product_id\":\"$PRODUCT_ID\",\"product_unit_id\":\"$UNIT_ID\",\"quantity\":2,\"unit_price\":$UNIT_PRICE}" >/dev/null
post_json "$BASE_URL/invoices/${INV2_ID}/items" "{\"product_id\":\"$PRODUCT_ID\",\"product_unit_id\":\"$UNIT_ID\",\"quantity\":3,\"unit_price\":$UNIT_PRICE}" >/dev/null
post_json "$BASE_URL/invoices/${INV2_ID}/items" "{\"product_id\":\"$PRODUCT_ID\",\"product_unit_id\":\"$UNIT_ID\",\"quantity\":1,\"unit_price\":$UNIT_PRICE}" >/dev/null
echo "Added 3 items to invoice 2"

echo
echo "Listing invoices (GET /invoices/all):"
curl -sS --max-time "$CURL_TIMEOUT" "$BASE_URL/invoices/all" | python -m json.tool

echo
echo "Done. You can now open $BASE_URL/docs and call GET /invoices/all."
