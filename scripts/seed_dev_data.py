import argparse
import csv
import random
import re
import string
from pathlib import Path
import sys

from sqlalchemy import select

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.product_table import Product, ProductStatus, ProductType
from app.models.product_unit_table import BaseUnit, ProductUnit
from app.models.stock_adjustment_table import StockAdjustment, StockAdjustmentReason


def _random_suffix(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def _generate_unique_sku(db, base: str) -> str:
    for _ in range(50):
        candidate = f"{base}-{_random_suffix()}"
        exists = db.execute(select(Product).where(Product.sku == candidate)).scalars().one_or_none()
        if not exists:
            return candidate
    raise RuntimeError("Failed to generate a unique SKU after multiple attempts")


def _slug_base(value: str) -> str:
    value = (value or "").strip().upper()
    value = re.sub(r"[^A-Z0-9]+", "-", value)
    value = value.strip("-")
    return value[:20] or "SKU"


def _parse_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    value = str(value).strip()
    if not value:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bool_yes_no(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    value = str(value).strip().lower()
    if value in {"yes", "y", "true", "1"}:
        return True
    if value in {"no", "n", "false", "0"}:
        return False
    return default


def _map_product_type(value: str | None) -> ProductType:
    value = (value or "").strip().lower()
    if value.startswith("med"):
        return ProductType.MEDICAL
    if "non" in value:
        return ProductType.NON_MEDICAL
    return ProductType.NON_MEDICAL


def _map_product_status(value: str | None) -> ProductStatus:
    value = (value or "").strip().lower()
    if value == "active":
        return ProductStatus.ACTIVE
    if value == "pending":
        return ProductStatus.PENDING
    if value == "inactive":
        return ProductStatus.INACTIVE
    return ProductStatus.ACTIVE


def _infer_base_unit(*, name: str, product_type: ProductType) -> BaseUnit:
    upper = (name or "").strip().upper()

    if any(token in upper for token in {"DROP", "DROPS"}):
        return BaseUnit.DROPS
    if any(token in upper for token in {"SYRUP"}):
        return BaseUnit.SYRUP
    if any(token in upper for token in {"SUSP", "SUSPENSION"}):
        return BaseUnit.SUSPENSION
    if any(token in upper for token in {"POWDER", "PWD"}):
        return BaseUnit.POWDER
    if any(token in upper for token in {"CREAM"}):
        return BaseUnit.CREAM
    if any(token in upper for token in {"OINT", "OINTMENT"}):
        return BaseUnit.OINTMENT
    if any(token in upper for token in {"GEL"}):
        return BaseUnit.GEL

    if any(token in upper for token in {"INJ", "INJECTION"}):
        return BaseUnit.VIAL
    if any(token in upper for token in {"AMP", "AMPOULE"}):
        return BaseUnit.AMPOULE

    if any(token in upper for token in {"CAP", "CAPS", "CAPSULE"}):
        return BaseUnit.CAPSULE
    if any(token in upper for token in {"TAB", "TABLET"}):
        return BaseUnit.TABLET
    if re.search(r"\b\d+\s?MG\b", upper) is not None:
        return BaseUnit.TABLET

    if product_type == ProductType.MEDICAL:
        return BaseUnit.TABLET

    return BaseUnit.PACK


def _seed_from_csv(
    db,
    *,
    csv_path: Path,
    count: int,
    with_stock: bool,
    random_sample: bool,
    fill_missing: bool,
    keep_empty_rate: float,
    min_stock: int,
    max_stock: int,
) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if random_sample and len(rows) > count:
        rows = random.sample(rows, k=count)
    else:
        rows = rows[:count]

    created = 0

    fallback_brands = ["Emzor", "GSK", "Pfizer", "Teva", "Afrab-Chem", "Fidson"]
    fallback_suppliers = ["Main Supplier", "Wholesale A", "Wholesale B", "Wholesale C"]
    fallback_return_policies = ["No returns", "7 days", "14 days"]

    def _maybe_empty_str(value: str | None, fallback: str) -> str | None:
        value = (value or "").strip()
        if value:
            return value
        if not fill_missing:
            return None
        if keep_empty_rate > 0 and random.random() < keep_empty_rate:
            return None
        return fallback

    def _maybe_empty_float(value: str | None, fallback: float) -> float | None:
        parsed = _parse_float(value)
        if parsed is not None:
            return parsed
        if not fill_missing:
            return None
        if keep_empty_rate > 0 and random.random() < keep_empty_rate:
            return None
        return fallback

    for row in rows:
        name = (row.get("PRODUCT NAME") or "").strip()
        if not name:
            continue

        sku_base = _slug_base(name)
        sku = _generate_unique_sku(db, base=sku_base)

        brand_name = _maybe_empty_str(row.get("BRAND NAME"), random.choice(fallback_brands))
        supplier_name = _maybe_empty_str(row.get("SUPPLIER"), random.choice(fallback_suppliers))

        barcode = (row.get("BARCODE") or "").strip()
        if not barcode and fill_missing and not (keep_empty_rate > 0 and random.random() < keep_empty_rate):
            barcode = str(random.randint(10**11, 10**12 - 1))
        if not barcode:
            barcode = None

        return_policy = _maybe_empty_str(
            row.get("ITEM RETURN POLICY"), random.choice(fallback_return_policies)
        )

        markup = _parse_float(row.get("MARKUP"))
        if markup is not None and markup < 0:
            markup = 0.0
        markup = markup if markup is not None else _maybe_empty_float(None, fallback=random.choice([5.0, 10.0, 15.0, 20.0]))

        reorder_level = _parse_int(row.get("STOCK THRESHOLD"), default=0)
        if reorder_level <= 0 and fill_missing:
            reorder_level = random.choice([1, 5, 10, 20])

        product = Product(
            sku=sku,
            name=name,
            base_unit=_infer_base_unit(name=name, product_type=_map_product_type(row.get("TYPE"))),
            brand_name=brand_name,
            supplier_name=supplier_name,
            barcode=barcode,
            markup_percent=markup,
            reorder_level=reorder_level,
            product_type=_map_product_type(row.get("TYPE")),
            dispense_without_prescription=_parse_bool_yes_no(
                row.get("DISPENSE WITHOUT PRESCRIPTION"), default=True
            ),
            return_policy=return_policy,
            status=_map_product_status(row.get("STATUS")),
        )

        db.add(product)
        db.flush()  # assigns Product.id without committing

        product_unit = ProductUnit(
            product_id=product.id,
            name=product.base_unit,
            multiplier_to_base=1,
            price_per_unit=0.0,
            is_default=True,
        )
        db.add(product_unit)

        if with_stock:
            raw_stock = row.get("STOCK")
            qty = _parse_int(raw_stock, default=-1)
            if qty < 0:
                qty = random.randint(min_stock, max_stock)
            qty = max(0, qty)
            product.quantity_on_hand = qty

            if qty != 0:
                adjustment = StockAdjustment(
                    product_id=product.id,
                    change_qty=qty,
                    reason=StockAdjustmentReason.INITIAL_IMPORT,
                    reference=str(csv_path.name),
                    note="Initial CSV seeded stock",
                )
                db.add(adjustment)

        created += 1

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Vigilis Pharmacy DB with sample products.")
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--random-sample", action="store_true")
    parser.add_argument("--with-stock", action="store_true")
    parser.add_argument("--fill-missing", action="store_true")
    parser.add_argument("--keep-empty-rate", type=float, default=0.05)
    parser.add_argument("--min-stock", type=int, default=0)
    parser.add_argument("--max-stock", type=int, default=50)
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be >= 1")

    if args.min_stock < 0 or args.max_stock < 0 or args.min_stock > args.max_stock:
        raise SystemExit("Invalid --min-stock/--max-stock values")

    if args.keep_empty_rate < 0 or args.keep_empty_rate > 1:
        raise SystemExit("--keep-empty-rate must be between 0 and 1")

    csv_path = Path(args.csv) if args.csv else None
    if csv_path is not None and not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    db = SessionLocal()
    created = 0

    try:
        if csv_path is not None:
            created = _seed_from_csv(
                db,
                csv_path=csv_path,
                count=args.count,
                with_stock=args.with_stock,
                random_sample=args.random_sample,
                fill_missing=args.fill_missing,
                keep_empty_rate=args.keep_empty_rate,
                min_stock=args.min_stock,
                max_stock=args.max_stock,
            )
        else:
            for i in range(args.count):
                sku = _generate_unique_sku(db, base=f"SKU-{i + 1:04d}")

                product = Product(
                    sku=sku,
                    name=f"Sample Product {i + 1}",
                    base_unit=random.choice([BaseUnit.PACK, BaseUnit.SACHET, BaseUnit.TABLET]),
                    brand_name=random.choice([None, "Emzor", "GSK", "Pfizer", "Teva"]),
                    supplier_name=random.choice([None, "Main Supplier", "Wholesale A", "Wholesale B"]),
                    barcode=random.choice([None, f"{random.randint(10**11, 10**12 - 1)}"]),
                    markup_percent=random.choice([None, 5.0, 10.0, 15.0, 20.0]),
                    reorder_level=random.choice([0, 5, 10, 20]),
                    product_type=random.choice([ProductType.MEDICAL, ProductType.NON_MEDICAL]),
                    dispense_without_prescription=random.choice([True, False]),
                    return_policy=random.choice([None, "No returns", "7 days", "14 days"]),
                    status=ProductStatus.ACTIVE,
                )

                db.add(product)
                db.flush()  # assigns Product.id without committing

                product_unit = ProductUnit(
                    product_id=product.id,
                    name=product.base_unit,
                    multiplier_to_base=1,
                    price_per_unit=0.0,
                    is_default=True,
                )
                db.add(product_unit)

                if args.with_stock:
                    qty = random.randint(args.min_stock, args.max_stock)
                    product.quantity_on_hand = qty

                    if qty != 0:
                        adjustment = StockAdjustment(
                            product_id=product.id,
                            change_qty=qty,
                            reason=StockAdjustmentReason.INITIAL_IMPORT,
                            reference="seed_dev_data",
                            note="Initial seeded stock",
                        )
                        db.add(adjustment)

                created += 1

        db.commit()
        print(f"Seed complete: created {created} products")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
