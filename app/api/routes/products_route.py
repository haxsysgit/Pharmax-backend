from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.models.stock_adjustment_table import StockAdjustment as StockAdjustmentTable
from app.schemas.stock_adjustment_schema import AdjustStockResponse, CreateStockAdjustment
from app.db.session import get_db
from app.models.product_table import Product as ProductTable
from app.schemas.products_schema import CreateProduct, ReadProduct, UpdateProduct
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/",response_model=ReadProduct)
def create_product(product:CreateProduct, db:Session=Depends(get_db),):
    # Prevent duplicate SKUs (SKU is the human-controlled unique identifier).
    stmt = select(ProductTable).where(ProductTable.sku == product.sku)
    result = db.execute(stmt).scalars().one_or_none()
    
    if result:
        raise HTTPException(status_code=400,detail="Product already exists")
    
    product = ProductTable(**product.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/", response_model=list[ReadProduct])
def read_products(query: Optional[str] = None, db:Session = Depends(get_db)):
    stmt = select(ProductTable)

    if query:
        # Simple search filter (you can expand this to sku/barcode later).
        stmt = stmt.where(or_(ProductTable.name.contains(query),ProductTable.brand_name.contains(query)))
    
    result = db.execute(stmt).scalars().all()

    return result 


@router.get("/{product_id}", response_model=ReadProduct)
def read_one_product(product_id:str, db:Session = Depends(get_db)):
    stmt = select(ProductTable).where(ProductTable.id == product_id)
    result = db.execute(stmt).scalars().one_or_none()
    
    if not result:
        raise HTTPException(status_code=404,detail="Product not found")
    return result


@router.post("/{product_id}/adjust-stock", response_model=AdjustStockResponse)
def adjust_stock(product_id:str, payload:CreateStockAdjustment, db:Session = Depends(get_db)):
    # Load the product we are adjusting stock for.
    stmt = select(ProductTable).where(ProductTable.id == product_id)
    result = db.execute(stmt).scalars().one_or_none()
    
    if not result:
        raise HTTPException(status_code=404,detail="Product not found")
    
    # Compute the next stock snapshot and block negative inventory.
    new_qty = result.quantity_on_hand + payload.change_qty
    # Update the product's current stock snapshot.
    result.quantity_on_hand = new_qty
    if new_qty < 0:
        raise HTTPException(status_code=400,detail="Cannot adjust stock to a negative quantity")
    
    # Create an audit row in stock_adjustments.
    adjustment_row = StockAdjustmentTable(**payload.model_dump(), product_id=result.id)
    db.add(adjustment_row)

    # One commit writes both the product update + the adjustment audit row.
    db.commit()
    db.refresh(result)
    db.refresh(adjustment_row)
    return {"adjustment": adjustment_row, "product": result}

@router.patch("/{product_id}", response_model=ReadProduct)
def update_product(product_id:str, product:UpdateProduct, db:Session = Depends(get_db)):
    stmt = select(ProductTable).where(ProductTable.id == product_id)
    result = db.execute(stmt).scalars().one_or_none()
    
    if not result:
        raise HTTPException(status_code=404,detail="Product not found")
    
    # Only update fields that were actually provided in the PATCH body.
    data = product.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400,detail="No data to update")

    # Apply the partial update to the existing ORM object.
    for key, value in data.items():
        setattr(result, key, value)

    db.commit()
    db.refresh(result)
    return result

    
@router.delete("/{product_id}")
def delete_product(product_id:str, db:Session = Depends(get_db)):
    stmt = select(ProductTable).where(ProductTable.id == product_id)
    result = db.execute(stmt).scalars().one_or_none()
    
    if not result:
        raise HTTPException(status_code=404,detail="Product not found")
    
    db.delete(result)
    db.commit()
    return {"status":"deleted","message":"Product deleted successfully"}

