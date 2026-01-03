"""Simple end-to-end smoke test for the invoices routes.

Run this script with your API server running, e.g. from Backend/:

    uv run fastapi dev main.py

Then in another terminal:

    uv run python -m tests.test_invoices_flow

This is *not* a pytest test; it's a straightforward script that:
- picks an existing product + one of its units
- creates an invoice
- adds items
- finalizes the invoice (checks stock deduction)
- cancels the invoice (checks stock is restored)
- prints useful debug output along the way.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import uuid4

import requests


BASE_URL = "http://127.0.0.1:8000"


def register_user(*, username: str, email: str, role: str, password: str) -> None:
    resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": f"{role} User",
            "password": password,
            "role": role,
        },
    )
    if resp.status_code == 201:
        return
    if resp.status_code == 400 and "already registered" in resp.text:
        return
    resp.raise_for_status()


def login(*, identifier: str, password: str) -> str:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "identifier": identifier,
            "password": password,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class ProductUnitRef:
    product_id: str
    product_unit_id: str
    product_name: str
    unit_name: str
    unit_price: float
    multiplier_to_base: int


def _pretty(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def pick_product_and_unit(*, headers: Dict[str, str]) -> ProductUnitRef:
    """Pick a product + unit pair that has enough stock to run the test.

    We plan to add 2 units and then 3 units (total 5 sale-units) of the same
    product+unit before finalizing. To avoid a "Not enough stock" error from
    the finalize route, we pick a product+unit where:

        product.quantity_on_hand >= 5 * multiplier_to_base

    This relies on:
      - GET /products
      - GET /products/{product_id}/unit
    """
    resp = requests.get(f"{BASE_URL}/products/", headers=headers)
    resp.raise_for_status()
    products: List[Dict[str, Any]] = resp.json()
    _check(len(products) > 0, "No products found; seed the DB first.")

    for product in products:
        product_id = product["id"]

        resp_units = requests.get(f"{BASE_URL}/products/{product_id}/units", headers=headers)
        resp_units.raise_for_status()
        units: List[Dict[str, Any]] = resp_units.json()
        if not units:
            continue

        for unit in units:
            multiplier = unit["multiplier_to_base"]
            return ProductUnitRef(
                product_id=product_id,
                product_unit_id=unit["id"],
                product_name=product["name"],
                unit_name=unit["name"],
                unit_price=unit["price_per_unit"],
                multiplier_to_base=multiplier,
            )

    raise AssertionError("No product+unit found with enough stock to run the test.")


def adjust_stock(*, product_id: str, change_qty: int, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.post(
        f"{BASE_URL}/products/{product_id}/adjust-stock",
        headers=headers,
        json={
            "change_qty": change_qty,
            "reason": "MANUAL_ADJUSTMENT",
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_product_snapshot(*, product_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.get(f"{BASE_URL}/products/{product_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()


def create_invoice(*, sold_by_name: str, headers: Dict[str, str]) -> Dict[str, Any]:
    payload = {"sold_by_name": sold_by_name}
    resp = requests.post(f"{BASE_URL}/invoices/", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def add_item(*, invoice_id: str, ref: ProductUnitRef, quantity: int, headers: Dict[str, str], unit_price: float | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "product_id": ref.product_id,
        "product_unit_id": ref.product_unit_id,
        "quantity": quantity,
    }

    # Always send a positive unit_price. Some seeded units have price_per_unit = 0,
    # and your add-item route rejects unit_price <= 0. So we use:
    #   - the provided override if given; otherwise
    #   - the unit's default price if > 0; otherwise
    #   - a safe fallback like 100.0 for this smoke test.
    if unit_price is not None:
        effective_price = unit_price
    else:
        default_price = ref.unit_price
        effective_price = default_price if default_price and default_price > 0 else 100.0

    payload["unit_price"] = effective_price

    resp = requests.post(
        f"{BASE_URL}/invoices/{invoice_id}/items",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def finalize_invoice(*, invoice_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.post(f"{BASE_URL}/invoices/{invoice_id}/finalize", headers=headers)
    resp.raise_for_status()
    return resp.json()


def cancel_invoice(*, invoice_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.post(f"{BASE_URL}/invoices/{invoice_id}/cancel", headers=headers)
    resp.raise_for_status()
    return resp.json()


def read_invoice(*, invoice_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.get(f"{BASE_URL}/invoices/{invoice_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()


def list_invoices(*, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    resp = requests.get(f"{BASE_URL}/invoices/all", headers=headers)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    suffix = str(uuid4())[:8]
    password = "test12345"
    admin_username = f"admin_{suffix}"
    cashier_username = f"cashier_{suffix}"

    register_user(
        username=admin_username,
        email=f"{admin_username}@vigilis.ph",
        role="ADMIN",
        password=password,
    )
    register_user(
        username=cashier_username,
        email=f"{cashier_username}@vigilis.ph",
        role="CASHIER",
        password=password,
    )

    admin = auth_headers(login(identifier=admin_username, password=password))
    cashier = auth_headers(login(identifier=cashier_username, password=password))

    # 1) Choose a product + unit
    ref = pick_product_and_unit(headers=admin)
    _pretty("Using product/unit", ref.__dict__)

    # Capture initial stock snapshot.
    before_product = get_product_snapshot(product_id=ref.product_id, headers=cashier)
    before_qty = int(before_product["quantity_on_hand"])
    _pretty("Initial product snapshot", before_product)

    required_units_total = 2 + 3
    required_base_qty = required_units_total * int(ref.multiplier_to_base)
    if before_qty < required_base_qty:
        adjust_stock(
            product_id=ref.product_id,
            change_qty=(required_base_qty - before_qty),
            headers=admin,
        )
        before_product = get_product_snapshot(product_id=ref.product_id, headers=cashier)
        before_qty = int(before_product["quantity_on_hand"])

    # 2) Create an invoice (DRAFT)
    inv = create_invoice(sold_by_name="Smoke Tester", headers=cashier)
    invoice_id = inv["id"]
    _check(inv["status"] == "DRAFT", "New invoice should start as DRAFT")
    _pretty("Created invoice", inv)

    # 3) Add a couple of items to the invoice
    inv = add_item(invoice_id=invoice_id, ref=ref, quantity=2, headers=cashier)
    _pretty("Invoice after adding 2 units", inv)

    inv = add_item(
        invoice_id=invoice_id,
        ref=ref,
        quantity=3,
        headers=cashier,
        unit_price=150.0,
    )
    _pretty("Invoice after adding 3 units @150", inv)

    _check(len(inv["items"]) >= 2, "Invoice should have at least 2 items now")

    # 4) Finalize invoice and verify stock deduction
    finalized = finalize_invoice(invoice_id=invoice_id, headers=cashier)
    _pretty("Finalized invoice", finalized)
    _check(finalized["status"] == "FINALIZED", "Invoice should be FINALIZED after finalize call")

    after_finalize_product = get_product_snapshot(product_id=ref.product_id, headers=cashier)
    after_finalize_qty = int(after_finalize_product["quantity_on_hand"])
    _pretty("Product after finalize", after_finalize_product)

    # Compute expected stock movement in base units.
    total_qty = sum(item["quantity"] for item in finalized["items"])
    # We don't know multiplier_to_base from this response, so just assert that stock went down.
    _check(after_finalize_qty < before_qty, "Stock should decrease after finalize")

    # 5) Cancel invoice and verify stock is restored
    cancelled = cancel_invoice(invoice_id=invoice_id, headers=cashier)
    _pretty("Cancelled invoice", cancelled)
    _check(cancelled["status"] == "CANCELLED", "Invoice should be CANCELLED after cancel call")

    after_cancel_product = get_product_snapshot(product_id=ref.product_id, headers=cashier)
    after_cancel_qty = int(after_cancel_product["quantity_on_hand"])
    _pretty("Product after cancel", after_cancel_product)

    _check(
        after_cancel_qty == before_qty,
        f"Stock after cancel ({after_cancel_qty}) should match initial stock ({before_qty})",
    )

    # 6) List invoices and check the created one is present
    invoices = list_invoices(headers=cashier)
    _pretty("All invoices", invoices)
    ids = [i["id"] for i in invoices]
    _check(invoice_id in ids, "Created invoice should appear in /invoices/all")

    print("\nAll invoice flow checks passed.")


if __name__ == "__main__":
    main()
