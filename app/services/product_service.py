from sqlalchemy.orm import Session
from app.models.product_table import Product
from app.models.stock_adjustment_table import StockAdjustment
from app.services.audit_service import AuditService
from contextlib import contextmanager
from typing import Optional, List
from uuid import uuid4


class ProductService:
    """Service for managing product operations with audit logging."""

    @staticmethod
    @contextmanager
    def transaction(db: Session):
        """Context manager for safe transaction handling."""
        try:
            yield
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create_product(db: Session, name: str, description: Optional[str] = None, quantity_on_hand: int = 0, user_id: Optional[str] = None) -> Product:
        """Create a new product.
        
        Args:
            db: Database session
            name: Product name
            description: Optional product description
            quantity_on_hand: Initial stock quantity
            user_id: ID of user creating product
            
        Returns:
            Created product
        """
        product = Product(
            id=str(uuid4()),
            name=name,
            description=description,
            quantity_on_hand=quantity_on_hand
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        
        # Log product creation
        AuditService.log_action(
            db=db,
            user_id=user_id or product.id,
            action="CREATE",
            resource_type="PRODUCT",
            resource_id=product.id,
            details={
                "name": name,
                "description": description,
                "initial_quantity": quantity_on_hand,
                "created_by": user_id
            }
        )
        
        return product

    @staticmethod
    def update_product(db: Session, product: Product, name: Optional[str] = None, description: Optional[str] = None, user_id: Optional[str] = None) -> Product:
        """Update product details.
        
        Args:
            db: Database session
            product: Product to update
            name: Optional new name
            description: Optional new description
            user_id: ID of user updating product
            
        Returns:
            Updated product
        """
        old_values = {
            "name": product.name,
            "description": product.description
        }
        
        if name is not None:
            product.name = name
        if description is not None:
            product.description = description
            
        db.commit()
        db.refresh(product)
        
        # Log update if anything changed
        if old_values["name"] != product.name or old_values["description"] != product.description:
            AuditService.log_action(
                db=db,
                user_id=user_id or product.id,
                action="UPDATE",
                resource_type="PRODUCT",
                resource_id=product.id,
                details={
                    "old_values": old_values,
                    "new_values": {
                        "name": product.name,
                        "description": product.description
                    },
                    "updated_by": user_id
                }
            )
        
        return product

    @staticmethod
    def delete_product(db: Session, product: Product, user_id: Optional[str] = None) -> bool:
        """Delete a product (soft delete recommended in production).
        
        Args:
            db: Database session
            product: Product to delete
            user_id: ID of user deleting product
            
        Returns:
            True if deleted successfully
        """
        # Log deletion before removing
        AuditService.log_action(
            db=db,
            user_id=user_id or product.id,
            action="DELETE",
            resource_type="PRODUCT",
            resource_id=product.id,
            details={
                "name": product.name,
                "description": product.description,
                "quantity_at_deletion": product.quantity_on_hand,
                "deleted_by": user_id
            }
        )
        
        db.delete(product)
        db.commit()
        
        return True

    @staticmethod
    def adjust_stock(db: Session, product: Product, change_qty: int, reason: str, reference: Optional[str] = None, note: Optional[str] = None, user_id: Optional[str] = None, commit: bool = True) -> StockAdjustment:
        """Adjust the stock for a product and create a stock adjustment record.

        Args:
            db: Database session
            product: Product instance to adjust
            change_qty: Positive or negative integer to change stock
            reason: Reason for adjustment
            reference: Optional external reference
            note: Optional note
            user_id: ID of the user performing the adjustment
            commit: If True, commits automatically
            
        Returns:
            Created stock adjustment record
        """
        old_quantity = product.quantity_on_hand
        new_qty = old_quantity + change_qty
        
        if new_qty < 0:
            raise ValueError("Cannot adjust stock to a negative quantity")

        # Update product stock
        product.quantity_on_hand = new_qty

        # Create adjustment record
        adjustment = StockAdjustment(
            id=str(uuid4()),
            product_id=product.id,
            change_qty=change_qty,
            reason=reason,
            reference=reference,
            note=note,
            created_by_user_id=user_id,
        )

        db.add(product)
        db.add(adjustment)

        if commit:
            try:
                db.commit()
                
                # Log stock adjustment
                AuditService.log_action(
                    db=db,
                    user_id=user_id or product.id,
                    action="ADJUST_STOCK",
                    resource_type="PRODUCT",
                    resource_id=product.id,
                    details={
                        "product_name": product.name,
                        "change_qty": change_qty,
                        "reason": reason,
                        "old_quantity": old_quantity,
                        "new_quantity": new_qty,
                        "reference": reference,
                        "adjusted_by": user_id
                    }
                )
                
            except Exception:
                db.rollback()
                raise

        return adjustment

    @staticmethod
    def get_product_by_id(db: Session, product_id: str) -> Optional[Product]:
        """Get product by ID.
        
        Args:
            db: Database session
            product_id: Product ID
            
        Returns:
            Product or None
        """
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def list_products(db: Session, name_filter: Optional[str] = None, min_stock: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Product]:
        """List products with optional filtering.
        
        Args:
            db: Database session
            name_filter: Optional name filter (partial match)
            min_stock: Optional minimum stock filter
            limit: Max results to return
            offset: Results offset for pagination
            
        Returns:
            List of products
        """
        query = db.query(Product)
        
        if name_filter:
            query = query.filter(Product.name.ilike(f"%{name_filter}%"))
        if min_stock is not None:
            query = query.filter(Product.quantity_on_hand >= min_stock)
            
        return query.order_by(Product.name).offset(offset).limit(limit).all()

    @staticmethod
    def get_low_stock_products(db: Session, threshold: int = 10) -> List[Product]:
        """Get products with stock below threshold.
        
        Args:
            db: Database session
            threshold: Stock threshold
            
        Returns:
            List of products with low stock
        """
        return db.query(Product).filter(
            Product.quantity_on_hand < threshold).order_by(Product.quantity_on_hand.asc()).all()
