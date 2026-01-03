from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import require_role
from app.schemas.stock_adjustment_schema import AdjustStockResponse, CreateStockAdjustment
from app.schemas.products_schema import CreateProduct, ReadProduct, UpdateProduct
from app.services.product_service import ProductService
from app.models.user_table import UserRole
from app.models.product_table import Product as ProductTable
from app.models.product_unit_table import ProductUnit
from app.schemas.product_unit_schema import ReadProductUnit
from app.db.session import get_db

router = APIRouter()


@router.post("/", response_model=ReadProduct)
def create_product(
    product: CreateProduct,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Create a new product."""
    # Check for existing SKU
    existing = db.query(ProductTable).filter(ProductTable.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    new_product = ProductService.create_product(
        db=db,
        name=product.name,
        description=product.description,
        quantity_on_hand=product.quantity_on_hand or 0,
        user_id=current_user.id
    )
    
    return new_product


@router.get("/", response_model=list[ReadProduct])
def list_products(
    name: Optional[str] = None,
    min_stock: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES))
):
    """List products with optional filtering."""
    products = ProductService.list_products(
        db=db,
        name_filter=name,
        min_stock=min_stock,
        limit=limit,
        offset=offset
    )
    
    return products


@router.get("/{product_id}", response_model=ReadProduct)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES))
):
    """Get product by ID."""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.get("/{product_id}/units", response_model=list[ReadProductUnit])
def get_product_units(
    product_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES))
):
    """Get product units."""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    units = db.query(ProductUnit).filter(ProductUnit.product_id == product_id).all()
    return units


@router.post("/{product_id}/adjust-stock", response_model=AdjustStockResponse)
def adjust_stock(product_id: str, payload: CreateStockAdjustment, 
                db: Session = Depends(get_db), current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER))
):
    """Adjust product stock."""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        adjustment = ProductService.adjust_stock(
            db=db,
            product=product,
            change_qty=payload.change_qty,
            reason=payload.reason.value,
            reference=payload.reference,
            note=payload.note,
            user_id=current_user.id
        )
        
        return {"product": product, "adjustment": adjustment}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{product_id}", response_model=ReadProduct)
def update_product(
    product_id: str,
    product_update: UpdateProduct,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Update product details."""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Only update provided fields
    update_data = product_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    updated_product = ProductService.update_product(
        db=db,
        product=product,
        name=update_data.get("name"),
        description=update_data.get("description"),
        user_id=current_user.id
    )
    
    return updated_product


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN))
):
    """Delete a product."""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product has invoice history
    from app.models.invoice_item_table import InvoiceItem
    invoice_ref = db.query(InvoiceItem).filter(InvoiceItem.product_id == product_id).first()
    if invoice_ref:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete product with invoice history"
        )
    
    ProductService.delete_product(db=db, product=product, user_id=current_user.id)
    
    return {"status": "deleted", "message": "Product deleted successfully", "product": product}
