from sqlalchemy.orm import Session
from app.models.product_unit_table import ProductUnit
from app.models.product_table import BaseUnit
from app.services.audit_service import AuditService
from contextlib import contextmanager
from sqlalchemy import select


class ProductUnitService:

    @staticmethod
    @contextmanager
    def transaction(db: Session):
        try:
            yield
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create_unit(db: Session, product_id: str, name: BaseUnit, price_per_unit: float, multiplier_to_base: int,
    ) -> ProductUnit:

        if multiplier_to_base <= 0:
            raise ValueError("multiplier_to_base must be greater than 0")

        with ProductUnitService.transaction(db):

            stmt = select(ProductUnit.id).where(
                ProductUnit.product_id == product_id,
                ProductUnit.name == name,
            )
            exists = db.execute(stmt).scalar_one_or_none()

            if exists:
                raise ValueError(f"Unit '{name}' already exists for this product")

            unit = ProductUnit(
                product_id=product_id,
                name=name,
                multiplier_to_base=multiplier_to_base,
                price_per_unit=price_per_unit,
            )

            db.add(unit)

            AuditService.log_action(
                db=db,
                action="CREATE",
                resource_type="PRODUCT_UNIT",
                resource_id=unit.id,
                details={
                    "product_id": product_id,
                    "name": name,
                    "price_per_unit": price_per_unit,
                    "multiplier_to_base": multiplier_to_base,
                },
            )

        db.refresh(unit)
        return unit
