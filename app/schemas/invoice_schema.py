from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.invoice_table import InvoiceStatus
from app.schemas.invoice_item_schema import ReadInvoiceItem


class ReadInvoice(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    sold_by_id: str
    name: Optional[str] = None
    status: InvoiceStatus
    created_at: datetime
    items: list[ReadInvoiceItem]
    total_amount: Optional[float] = None