from sqlalchemy.orm import Session
from uuid import uuid4
from typing import List
from contextlib import contextmanager
from sqlalchemy import select
import re
from datetime import datetime, timezone 
from app.models.product_table import Product, ProductType, ProductStatus
from app.models.stock_adjustment_table import StockAdjustment
from app.services.audit_service import AuditService
from app.models.product_unit_table import BaseUnit
from app.services.product_unit_service import ProductUnitService
from app.schemas.product_schema import CreateProduct


# SKU generation constants
TYPE_PREFIX = {ProductType.MEDICAL: "MED", ProductType.NON_MEDICAL: "NON"}
STOP_WORDS = {"TABLET", "TABLETS", "CAPSULE", "CAPSULES", "MG", "ML", "SYRUP", "CREAM", "OINTMENT"}


class ProductService:

    # ================= SKU =================

    @staticmethod
    def _generate_sku(db: Session, name: str, product_type: ProductType) -> str:
        type_prefix = TYPE_PREFIX.get(product_type, "GEN")

        tokens = re.findall(r"[A-Z0-9]+", name.upper())
        tokens = [t for t in tokens if t not in STOP_WORDS]

        name_code = "-".join(tokens[:3])[:10]
        base = f"{type_prefix}-{name_code}"

        seq = 1
        while True:
            sku = f"{base}-{seq:03d}"
            stmt = select(Product.id).where(Product.sku == sku)
            exists = db.execute(stmt).scalar_one_or_none()
            if not exists:
                return sku
            seq += 1

    @staticmethod
    def _validate_or_generate_sku(db: Session, name: str, product_type: ProductType) -> str:
        return ProductService._generate_sku(db, name, product_type)

    # ================= TX =================

    @staticmethod
    @contextmanager
    def transaction(db: Session):
        try:
            yield
            db.commit()
        except Exception:
            db.rollback()
            raise

    # ================= CREATE =================

    @staticmethod
    def create_product(db: Session, data: CreateProduct, user_id: str) -> Product:
    
        sku = ProductService._validate_or_generate_sku(db, data.name, data.product_type)

        with ProductService.transaction(db):
            product = Product(
                sku=sku,
                name=data.name,
                base_unit=data.base_unit,
                brand_name=data.brand_name,
                supplier_name=data.supplier_name,
                barcode=data.barcode,
                markup_percent=data.markup_percent,
                reorder_level=data.reorder_level,
                product_type=data.product_type,
                dispense_without_prescription=data.dispense_without_prescription,
                return_policy=data.return_policy,
                status=data.status,
                quantity_on_hand=data.initial_quantity,
            )

            db.add(product)
            db.flush()  # ensure product.id exists

            # Create the base unit
            base_unit_obj = ProductUnitService.create_unit(
                db,
                product_id=product.id,
                unit=data.base_unit,
                price_per_unit=data.price_per_unit,
                multiplier_to_base=data.multiplier_to_base,
            )

            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="CREATE",
                resource_type="PRODUCT",
                resource_id=product.id,
                details={
                    "sku": product.sku,
                    "name": product.name,
                    "product_type": product.product_type,
                },
            )

        db.refresh(product)  # now product.product_units contains the base unit automatically
        return product
    

    # ================= UPDATE =================

    @staticmethod
    def update_product(db: Session, product: Product, updates: dict, user_id: str | None = None) -> Product:
        old_values = {k: getattr(product, k) for k in updates}

        with ProductService.transaction(db):
            for field, value in updates.items():
                setattr(product, field, value)

            new_values = {k: getattr(product, k) for k in updates}

            if old_values != new_values:
                AuditService.log_action(
                    db=db,
                    user_id=user_id,
                    action="UPDATE",
                    resource_type="PRODUCT",
                    resource_id=product.id,
                    details={
                        "sku": product.sku,
                        "name": product.name,
                        "old_values": old_values,
                        "new_values": new_values,
                    },
                )

        db.refresh(product)
        return product

    # ================= DELETE =================

    @staticmethod
    def hard_delete_product(db: Session, product: Product, user_id: str | None = None) -> None:
        with ProductService.transaction(db):
            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="DELETE",
                resource_type="PRODUCT",
                resource_id=product.id,
                details={
                    "sku": product.sku,
                    "name": product.name,
                    "quantity_at_deletion": product.quantity_on_hand,
                },
            )
            

            db.delete(product)

    @staticmethod
    def soft_delete_product(db: Session, product: Product, user_id: str | None = None) -> None:
        with ProductService.transaction(db):
            product.status = ProductStatus.DELETED
            product.deleted_at = datetime.now(timezone.utc)

            AuditService.log_action(
                db=db,
                user_id=user_id,
                resource_id=product.id,
                resource_type="PRODUCT",
                action="SOFT_DELETE",
                details={
                    "sku": product.sku,
                    "name": product.name,
                    "quantity_at_deletion": product.quantity_on_hand,
                },
            )


    @staticmethod
    def restore_product(db: Session, product: Product, user_id: str | None):
        stmt = select(Product).where(Product.id == product.id, Product.deleted_at.isnot(None))
        product = db.execute(stmt).scalar_one_or_none()

        with ProductService.transaction(db):
            product.status = ProductStatus.ACTIVE
            product.deleted_at = None

            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="RESTORE PRODUCT",
                resource_id=product.id,
                resource_type="PRODUCT",
                details={
                    "sku": product.sku,
                    "name": product.name,
                    "quantity_at_restore": product.quantity_on_hand,
                }
            )
    # ================= STOCK =================

    @staticmethod
    def adjust_stock(
        db: Session,
        product: Product,
        change_qty: int,
        reason: str,
        reference: str | None = None,
        note: str | None = None,
        user_id: str | None = None,
    ) -> StockAdjustment:

        old_qty = product.quantity_on_hand
        new_qty = old_qty + change_qty

        if new_qty < 0:
            raise ValueError("Cannot adjust stock to a negative quantity")

        with ProductService.transaction(db):
            product.quantity_on_hand = new_qty

            adjustment = StockAdjustment(
                id=str(uuid4()),
                product_id=product.id,
                change_qty=change_qty,
                reason=reason,
                reference=reference,
                note=note,
                created_by_user_id=user_id,
            )

            db.add(adjustment)

            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="ADJUST_STOCK",
                resource_type="PRODUCT",
                resource_id=product.id,
                details={
                    "sku": product.sku,
                    "name": product.name,
                    "old_quantity": old_qty,
                    "new_quantity": new_qty,
                    "change_qty": change_qty,
                    "reason": reason,
                    "reference": reference,
                },
            )

        return adjustment

    # ================= READ =================

    @staticmethod
    def get_product_by_id(db: Session, product_id: str) -> Product | None:
        stmt = select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
        return db.execute(stmt).scalar_one_or_none()
    

    @staticmethod
    def list_products(
        db: Session,
        name_filter: str | None = None,
        min_stock: int | None = None,
        limit: int = 50,
        offset: int = 0,
        deleted: bool = False,
    ) -> List[Product]:

        if deleted:
            stmt = select(Product).where(Product.deleted_at.isnot(None))
        else:
            stmt = select(Product).where(Product.deleted_at.is_(None))

        if name_filter:
            stmt = stmt.where(Product.name.ilike(f"%{name_filter}%"))
        if min_stock is not None:
            stmt = stmt.where(Product.quantity_on_hand >= min_stock)

        stmt = stmt.order_by(Product.name).offset(offset).limit(limit)
        return db.execute(stmt).scalars().all()
    
