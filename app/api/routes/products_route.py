from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user_table import UserRole
from app.models.product_unit_table import ProductUnit
from app.schemas.product_schema import CreateProduct, ReadProduct, UpdateProduct
from app.schemas.product_unit_schema import ReadProductUnit
from app.schemas.stock_adjustment_schema import AdjustStockResponse, CreateStockAdjustment
from app.services.product_service import ProductService
from app.models.invoice_item_table import InvoiceItem


router = APIRouter(prefix="/products", tags=["Products"])


# ================= CREATE =================

@router.post("/", response_model=ReadProduct, status_code=status.HTTP_201_CREATED)
def create_product(data: CreateProduct, db: Session = Depends(get_db), current_user=Depends(require_role(UserRole.ADMIN)),
) -> ReadProduct:
    try:
        return ProductService.create_product(
            db=db,
            data=data,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================= LIST =================

@router.get("/", response_model=List[ReadProduct])
def list_products(
    name: str | None = None,
    min_stock: int | None = None,
    limit: int = 50,
    offset: int = 0,
    deleted: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES)
    ),
):
    return ProductService.list_products(
        db=db,
        name_filter=name,
        min_stock=min_stock,
        limit=limit,
        offset=offset,
        deleted=deleted,
    )


# ================= READ =================

@router.get("/{product_id}", response_model=ReadProduct)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES)
    ),
):
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ================= UNITS =================

@router.get("/{product_id}/units", response_model=List[ReadProductUnit])
def get_product_units(
    product_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES)
    ),
):
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    stmt = select(ProductUnit).where(ProductUnit.product_id == product_id)
    return db.execute(stmt).scalars().all()


# ================= STOCK =================

@router.post("/{product_id}/adjust-stock", response_model=AdjustStockResponse)
def adjust_stock(
    product_id: str,
    payload: CreateStockAdjustment,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN, UserRole.CASHIER)),
):
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
            user_id=current_user.id,
        )
        return AdjustStockResponse(product=product, adjustment=adjustment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================= UPDATE =================

@router.patch("/{product_id}", response_model=ReadProduct)
def update_product(
    product_id: str,
    payload: UpdateProduct,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    return ProductService.update_product(
        db=db,
        product=product,
        updates=update_data,
        user_id=current_user.id,
    )


# ================= DELETE =================

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    hard_delete: bool = False, 
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")


    stmt = select(InvoiceItem).where(InvoiceItem.product_id == product_id)
    if db.execute(stmt).scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete product with invoice history",)

    if hard_delete:
        ProductService.hard_delete_product(db=db, product=product, user_id=current_user.id)
        return

    ProductService.soft_delete_product(db=db, product=product, user_id=current_user.id)
