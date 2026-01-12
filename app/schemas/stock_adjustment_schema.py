from datetime import datetime

from pydantic import BaseModel

from app.models.stock_adjustment_table import StockAdjustmentReason
from app.schemas.product_schema import ReadProduct


class StockAdjustmentBase(BaseModel):
    # Positive means stock increases; negative means stock decreases.
    change_qty: int

    # Why the stock changed (used for audit/reporting).
    reason: StockAdjustmentReason
    reference: str | None = None
    note: str | None = None


class CreateStockAdjustment(StockAdjustmentBase):
    pass

class ReadStockAdjustment(StockAdjustmentBase):
    model_config = {"from_attributes": True}
    id: str
    product_id: str
    created_at: datetime
    created_by_user_id: str | None = None

# Combined response schema for stock adjustments
class AdjustStockResponse(BaseModel):
    # Combined response: audit record + updated product snapshot (UI convenience).
    model_config = {"from_attributes": True}
    adjustment: ReadStockAdjustment
    product: ReadProduct