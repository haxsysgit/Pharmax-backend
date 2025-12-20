from fastapi import APIRouter,Depends,HTTPException

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.invoice_schema import CreateInvoice,ReadInvoice
from app.schemas.invoice_item_schema import AddInvoiceItem
from app.models.invoice_table import Invoice as InvoiceTable
from app.models.invoice_item_table import InvoiceItem as InvoiceItemTable
from app.models.invoice_table import InvoiceStatus
from app.models.product_table import Product as ProductTable
from app.models.product_unit_table import ProductUnit as ProductUnitTable


from app.db.session import get_db

def _get_invoice_or_404(db, invoice_id):
    stmt = select(InvoiceTable).where(InvoiceTable.id == invoice_id)
    invoice = db.execute(stmt).scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


def _get_product_or_404(db, product_id):
    stmt = select(ProductTable).where(ProductTable.id == product_id)
    product = db.execute(stmt).scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

def _get_unit_or_404(db, unit_id):
    stmt = select(ProductUnitTable).where(ProductUnitTable.id == unit_id)
    unit= db.execute(stmt).scalar_one_or_none()
    
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    return unit

def _build_invoice_response(invoice: InvoiceTable):
    total = sum(float(i.line_total) for i in invoice.items)
    return {
        "id": invoice.id,
        "sold_by_name": invoice.sold_by_name,
        "status": invoice.status,
        "created_at": invoice.created_at,
        "items": invoice.items,
        "total": total,
    }


router = APIRouter()

@router.post("/",response_model=ReadInvoice)
def create_invoice(invoice: CreateInvoice, db:Session=Depends(get_db)):
    invoice= InvoiceTable(**invoice.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _build_invoice_response(invoice)


@router.post("/{invoice_id}/items",response_model=ReadInvoice)
def add_invoice_item(invoice_id: str,item: AddInvoiceItem, db:Session=Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)
    unit = _get_unit_or_404(db, item.product_unit_id)
    product = _get_product_or_404(db, item.product_id)

    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Invoice is not in draft status")
    
    if unit.product_id != product.id:
        raise HTTPException(status_code=400, detail="Unit does not belong to the product")
    
    unit_price = item.unit_price if item.unit_price is not None else unit.price_per_unit
    if unit_price <= 0:
        raise HTTPException(status_code=400, detail="Unit price must be greater than 0")
        
    line_total = item.quantity * unit_price

    invoice_item = InvoiceItemTable(
        invoice_id=invoice_id,
        product_id=product.id,
        product_unit_id=unit.id,
        quantity=item.quantity,
        unit_price=unit_price,
        line_total=line_total
    )

    invoice_item.product = product
    invoice_item.product_unit = unit
    
    invoice.items.append(invoice_item)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _build_invoice_response(invoice)


@router.get("/all", response_model=list[ReadInvoice])
def list_invoices(db: Session = Depends(get_db)):
    stmt = select(InvoiceTable).order_by(InvoiceTable.created_at.desc())
    invoices = db.execute(stmt).scalars().all()
    return [_build_invoice_response(inv) for inv in invoices]


@router.post("/{invoice_id}/finalize", response_model=ReadInvoice)
def finalize_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)

    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT invoices can be finalized")

    if len(invoice.items) == 0:
        # Business rule: you cannot finalize an invoice that has no line items.
        raise HTTPException(status_code=400, detail="Invoice has no items")

    for item in invoice.items:
        # Prefer already-loaded relationships to avoid extra queries, but fall back to safety.
        product = item.product or _get_product_or_404(db, item.product_id)
        unit = item.product_unit or _get_unit_or_404(db, item.product_unit_id)

        if unit.product_id != product.id:
            raise HTTPException(status_code=400, detail="Unit does not belong to the product")
        
        base_qty = item.quantity * unit.multiplier_to_base

        if product.quantity_on_hand < base_qty:
            raise HTTPException(status_code=400, detail="Not enough stock")

        # Deduct stock in memory; one commit after the loop will persist all changes together
        product.quantity_on_hand -= base_qty
    
    invoice.status = InvoiceStatus.FINALIZED
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return _build_invoice_response(invoice)


@router.post("/{invoice_id}/cancel", response_model=ReadInvoice)
def cancel_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)

    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Invoice is already cancelled")

    if invoice.status == InvoiceStatus.FINALIZED:
        # Reverse the stock deduction done at finalize time.
        for item in invoice.items:
            product = item.product or _get_product_or_404(db, item.product_id)
            unit = item.product_unit or _get_unit_or_404(db, item.product_unit_id)
            
            base_qty = item.quantity * unit.multiplier_to_base
            product.quantity_on_hand += base_qty
    elif invoice.status != InvoiceStatus.DRAFT:
        # At this point, only DRAFT invoices are cancellable without restocking.
        raise HTTPException(status_code=400, detail="Only DRAFT invoices can be cancelled")
    else:
        # For DRAFT invoices, there was no stock movement yet; simply drop the items.
        invoice.items = []
    
    invoice.status = InvoiceStatus.CANCELLED
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _build_invoice_response(invoice)


@router.get("/{invoice_id}",response_model=ReadInvoice)
def read_invoice(invoice_id: str, db:Session=Depends(get_db)):
    invoice = _get_invoice_or_404(db, invoice_id)

    return _build_invoice_response(invoice)
