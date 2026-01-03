from sqlalchemy.orm import Session
from app.models.invoice_table import Invoice, InvoiceStatus
from app.models.invoice_item_table import InvoiceItem
from app.models.product_table import Product
from app.models.product_unit_table import ProductUnit
from app.services.audit_service import AuditService
from typing import Optional, List
from decimal import Decimal
from uuid import uuid4


class InvoiceService:
    """Service for managing invoice operations with audit logging."""

    @staticmethod
    def create_invoice(db: Session, sold_by_id: str) -> Invoice:
        """Create a new draft invoice.
        
        Args:
            db: Database session
            sold_by_id: ID of user making the sale (required)
            customer_name: Optional customer name
            user_id: ID of user creating invoice
            
        Returns:
            Created invoice with DRAFT status
        """
        invoice = Invoice(
            id=str(uuid4()),
            sold_by_id=sold_by_id,
            status=InvoiceStatus.DRAFT
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Log invoice creation
        AuditService.log_action(
            db=db,
            user_id=sold_by_id or invoice.id,
            action="CREATE",
            resource_type="INVOICE",
            resource_id=invoice.id,
            details={
                "created_by": sold_by_id
            }
        )
        
        return invoice

    @staticmethod
    def add_item(db: Session, invoice: Invoice, product_id: str, product_unit_id: str, quantity: int, unit_price: Decimal, user_id: Optional[str] = None) -> InvoiceItem:
        """Add an item to a draft invoice.
        
        Args:
            db: Database session
            invoice: Invoice to add item to
            product_id: Product ID
            product_unit_id: Product unit ID
            quantity: Quantity in units
            unit_price: Price per unit
            user_id: ID of user adding item
            
        Returns:
            Created invoice item
        """
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Can only add items to DRAFT invoices")
        
        # Validate product and unit
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
            
        unit = db.query(ProductUnit).filter(ProductUnit.id == product_unit_id).first()
        if not unit or unit.product_id != product_id:
            raise ValueError("Invalid product unit")
        
        # Create invoice item
        item = InvoiceItem(
            id=str(uuid4()),
            invoice_id=invoice.id,
            product_id=product_id,
            product_unit_id=product_unit_id,
            quantity=quantity,
            unit_price=unit_price
        )
        
        db.add(item)
        db.commit()
        db.refresh(item)
        
        # Log item addition
        AuditService.log_action(
            db=db,
            user_id=user_id or invoice.user_id,
            action="ADD_ITEM",
            resource_type="INVOICE_ITEM",
            resource_id=item.id,
            details={
                "invoice_id": invoice.id,
                "product_id": product_id,
                "product_name": product.name,
                "quantity": quantity,
                "unit_price": float(unit_price),
                "added_by": user_id
            }
        )
        
        return item

    @staticmethod
    def finalize_invoice(db: Session, invoice: Invoice, user_id: Optional[str] = None):
        """Finalize a draft invoice and deduct stock.
        
        Args:
            db: Database session
            invoice: Invoice to finalize
            user_id: ID of user finalizing invoice
        """
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Only DRAFT invoices can be finalized")

        if not invoice.items:
            raise ValueError("Invoice has no items")

        # Check stock and deduct for each item
        for item in invoice.items:
            product: Product = item.product
            unit: ProductUnit = item.product_unit

            if unit.product_id != product.id:
                raise ValueError("Unit does not belong to product")

            base_qty = item.quantity * unit.multiplier_to_base

            if product.quantity_on_hand < base_qty:
                raise ValueError(f"Not enough stock for {product.name}. Available: {product.quantity_on_hand}, Required: {base_qty}")

            # Deduct stock
            product.quantity_on_hand -= base_qty

        # Update invoice status
        invoice.status = InvoiceStatus.FINALIZED
        
        # Calculate total amount
        total_amount = sum(item.quantity * item.unit_price for item in invoice.items)
        invoice.total_amount = total_amount
        
        db.commit()
        
        # Log finalization
        AuditService.log_action(
            db=db,
            user_id=user_id or invoice.user_id,
            action="FINALIZE",
            resource_type="INVOICE",
            resource_id=invoice.id,
            details={
                "total_amount": float(total_amount),
                "items_count": len(invoice.items),
                "finalized_by": user_id
            }
        )

    @staticmethod
    def cancel_invoice(db: Session, invoice: Invoice, reason: Optional[str] = None, user_id: Optional[str] = None):
        """Cancel an invoice and restore stock if finalized.
        
        Args:
            db: Database session
            invoice: Invoice to cancel
            reason: Optional cancellation reason
            user_id: ID of user canceling invoice
        """
        if invoice.status == InvoiceStatus.CANCELLED:
            raise ValueError("Invoice already cancelled")

        # If finalized, restore stock
        if invoice.status == InvoiceStatus.FINALIZED:
            for item in invoice.items:
                base_qty = item.quantity * item.product_unit.multiplier_to_base
                item.product.quantity_on_hand += base_qty

        elif invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Only DRAFT invoices can be cancelled")

        # Update status
        invoice.status = InvoiceStatus.CANCELLED
        
        db.commit()
        
        # Log cancellation
        AuditService.log_action(
            db=db,
            user_id=user_id or invoice.user_id,
            action="CANCEL",
            resource_type="INVOICE",
            resource_id=invoice.id,
            details={
                "cancellation_reason": reason,
                "cancelled_by": user_id,
                "previous_status": invoice.status.value
            }
        )

    @staticmethod
    def get_invoice_with_items(db: Session, invoice_id: str) -> Optional[Invoice]:
        """Get invoice with all items loaded.
        
        Args:
            db: Database session
            invoice_id: Invoice ID
            
        Returns:
            Invoice with items or None
        """
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    @staticmethod
    def list_invoices(db: Session, status: Optional[InvoiceStatus] = None, user_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Invoice]:
        """List invoices with optional filtering.
        
        Args:
            db: Database session
            status: Optional status filter
            user_id: Optional user filter
            limit: Max results to return
            offset: Results offset for pagination
            
        Returns:
            List of invoices
        """
        query = db.query(Invoice)
        
        if status:
            query = query.filter(Invoice.status == status)
        if user_id:
            query = query.filter(Invoice.user_id == user_id)
            
        return query.order_by(Invoice.created_at.desc()).offset(offset).limit(limit).all()
