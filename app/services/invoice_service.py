from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.models.invoice_table import Invoice, InvoiceStatus
from app.models.invoice_item_table import InvoiceItem
from app.models.product_table import Product
from app.models.product_unit_table import ProductUnit
from app.services.audit_service import AuditService
from decimal import Decimal
from contextlib import contextmanager


class InvoiceService:

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
    def create_invoice(db: Session, sold_by_id: str) -> Invoice:
        with InvoiceService.transaction(db):
            invoice = Invoice(
                sold_by_id=sold_by_id,
                status=InvoiceStatus.DRAFT,
            )

            db.add(invoice)

            AuditService.log_action(
                db=db,
                user_id=sold_by_id,
                action="CREATE",
                resource_type="INVOICE",
                resource_id=invoice.id,
                details={"created_by": sold_by_id},
            )

        db.refresh(invoice)
        return invoice

    # ================= ADD ITEM =================

    @staticmethod
    def add_item(
        db: Session,
        invoice: Invoice,
        product_id: str,
        product_unit_id: str,
        quantity: int,
        unit_price: Decimal,
        user_id: str,
    ) -> InvoiceItem:

        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Can only add items to DRAFT invoices")

        stmt = select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
        product = db.execute(stmt).scalar_one_or_none()
        if not product:
            raise ValueError("Product not found")

        stmt = select(ProductUnit).where(ProductUnit.id == product_unit_id)
        unit = db.execute(stmt).scalar_one_or_none()
        if not unit or unit.product_id != product.id:
            raise ValueError("Invalid product unit")

        with InvoiceService.transaction(db):
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=product_id,
                product_unit_id=product_unit_id,
                quantity=quantity,
                unit_price=unit_price,
            )

            db.add(item)

            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="ADD_ITEM",
                resource_type="INVOICE_ITEM",
                resource_id=item.id,
                details={
                    "invoice_id": invoice.id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                    "added_by": user_id,
                },
            )

        db.refresh(item)
        return item

    # ================= FINALIZE =================

    @staticmethod
    def finalize_invoice(db: Session, invoice: Invoice, user_id: str) -> None:
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Only DRAFT invoices can be finalized")

        if not invoice.items:
            raise ValueError("Invoice has no items")

        with InvoiceService.transaction(db):
            total = Decimal("0.00")

            for item in invoice.items:
                unit = item.product_unit
                product = item.product

                base_qty = item.quantity * unit.multiplier_to_base
                if product.quantity_on_hand < base_qty:
                    raise ValueError(f"Insufficient stock for {product.name}")

                product.quantity_on_hand -= base_qty
                total += item.quantity * item.unit_price

            invoice.status = InvoiceStatus.FINALIZED
            invoice.total_amount = total

            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="FINALIZE",
                resource_type="INVOICE",
                resource_id=invoice.id,
                details={
                    "total_amount": float(total),
                    "items_count": len(invoice.items),
                    "finalized_by": user_id,
                },
            )

    # ================= CANCEL =================

    @staticmethod
    def cancel_invoice(
        db: Session,
        invoice: Invoice,
        user_id: str,
        reason: str | None = None,
    ) -> None:

        if invoice.status == InvoiceStatus.CANCELLED:
            raise ValueError("Invoice already cancelled")

        with InvoiceService.transaction(db):
            if invoice.status == InvoiceStatus.FINALIZED:
                for item in invoice.items:
                    base_qty = (
                        item.quantity * item.product_unit.multiplier_to_base
                    )
                    item.product.quantity_on_hand += base_qty

            invoice.status = InvoiceStatus.CANCELLED

            AuditService.log_action(
                db=db,
                user_id=user_id,
                action="CANCEL",
                resource_type="INVOICE",
                resource_id=invoice.id,
                details={
                    "reason": reason,
                    "cancelled_by": user_id,
                },
            )

    @staticmethod
    def list_invoices(
        db: Session, 
        user_id: str | None, 
        status: InvoiceStatus | None = InvoiceStatus.FINALIZED,
        limit: int = 50,
        offset: int = 0
    ) -> list[Invoice]:
        
        stmt = select(Invoice).where(Invoice.sold_by_id == user_id) if user_id else select(Invoice)
        
        if status:
            stmt = stmt.where(Invoice.status == status)
        
        stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        invoices = db.execute(stmt).scalars().all()

        AuditService.log_action(
            db=db,
            user_id=user_id or "system",
            action="LIST",
            resource_type="INVOICE",
            resource_id=None,
            details={
                "status": status.value if status else None,
                "limit": limit,
                "offset": offset,
                "results_count": len(invoices),
                "filtered_by_user": user_id is not None,
            },
        )
        
        return invoices

    @staticmethod
    def get_invoice_by_id(db: Session, invoice_id: str) -> Invoice | None:
        """Get invoice by ID with relationships loaded."""
        stmt = select(Invoice).options(
            selectinload(Invoice.items).selectinload(InvoiceItem.product),
            selectinload(Invoice.items).selectinload(InvoiceItem.product_unit)
        ).where(Invoice.id == invoice_id)
        return db.execute(stmt).scalar_one_or_none()


                    

