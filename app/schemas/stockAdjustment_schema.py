from pydantic import BaseModel

from app.models.stock_adjustment_table import StockAdjustmentReason


class StockAdjustmentBase(BaseModel):
    product_id: str
    reason: StockAdjustmentReason
    quantity: int

class CreateStockAdjustment(StockAdjustmentBase):
    pass

class ReadStockAdjustment(StockAdjustmentBase):
    id: str
    created_at: datetime
    updated_at: datetime