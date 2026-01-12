from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from app.models.invoice_item_table import InvoiceItem
from app.core.dependencies import require_role, get_current_user
from app.services.invoice_service import InvoiceService
from app.schemas.invoice_schema import ReadInvoice
from app.schemas.invoice_item_schema import AddInvoiceItem
from app.models.invoice_table import Invoice as InvoiceTable, InvoiceStatus
from app.models.user_table import UserRole
from app.db.session import get_db


def _get_invoice_or_404(db: Session, invoice_id: str) -> InvoiceTable:
    """Get invoice with relationships or 404."""
    invoice = InvoiceService.get_invoice_by_id(db, invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def _build_invoice_response(invoice: InvoiceTable, name: str | None = None) -> ReadInvoice:
    """Build invoice response with calculated total."""
    total = sum(float(item.quantity * item.unit_price) for item in invoice.items) if invoice.items else 0.0
    
    return ReadInvoice(
        id=invoice.id,
        sold_by_id=invoice.sold_by_id,
        status=invoice.status,
        created_at=invoice.created_at,
        items=invoice.items,
        total_amount= total,
        name=name
    )


router = APIRouter()


@router.post("/", response_model=ReadInvoice)
def create_invoice(
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES))
):
    """Create a new invoice."""
    invoice = InvoiceService.create_invoice(
        db=db,
        sold_by_id=current_user.id,
    )
    
    return _build_invoice_response(invoice, name=current_user.full_name)


@router.post("/{invoice_id}/items", response_model=ReadInvoice)
def add_invoice_item(
    invoice_id: str,
    item: AddInvoiceItem,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES))
):
    """Add item to invoice."""
    invoice = _get_invoice_or_404(db, invoice_id)
    
    invoice_item = InvoiceService.add_item(
        db=db,
        invoice=invoice,
        product_id=item.product_id,
        product_unit_id=item.product_unit_id,
        quantity=item.quantity,
        unit_price=item.unit_price or 0.0,
        user_id=current_user.id
    )
    
    # Refresh invoice to get updated items
    db.refresh(invoice)
    return _build_invoice_response(invoice, name=current_user.full_name)


@router.get("/all", response_model=list[ReadInvoice])
def list_invoices(
    status: InvoiceStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER))
):
    """List invoices with optional filtering."""
    invoices = InvoiceService.list_invoices(
        db=db,
        status=status,
        user_id=current_user.id if current_user.role != UserRole.ADMIN else None,
        limit=limit,
        offset=offset
    )

    return [_build_invoice_response(inv, name=current_user.full_name) for inv in invoices]


@router.post("/{invoice_id}/finalize", response_model=ReadInvoice)
def finalize_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER))
):
    """Finalize an invoice."""
    invoice = _get_invoice_or_404(db, invoice_id)
    
    try:
        InvoiceService.finalize_invoice(db, invoice, user_id=current_user.id)
        db.refresh(invoice)
        return _build_invoice_response(invoice, name=current_user.full_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/cancel", response_model=ReadInvoice)
def cancel_invoice(
    invoice_id: str,
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER))
):
    """Cancel an invoice."""
    invoice = _get_invoice_or_404(db, invoice_id)
    
    try:
        InvoiceService.cancel_invoice(db, invoice, reason=reason, user_id=current_user.id)
        db.refresh(invoice)
        return _build_invoice_response(invoice, name=current_user.full_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}", response_model=ReadInvoice)
def read_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.CASHIER,UserRole.SALES))
):
    """Get invoice by ID."""
    invoice = _get_invoice_or_404(db, invoice_id)
    return _build_invoice_response(invoice, name=current_user.full_name)
