from typing import Optional

from pydantic import BaseModel, Field


class AddInvoiceItem(BaseModel):
    product_id: str
    product_unit_id: str
    quantity: int = Field(ge=1)
    unit_price: Optional[float] = None

class ProductMini(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str

class UnitMini(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str

class ReadInvoiceItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    quantity: int
    unit_price: float
    line_total: float
    product: ProductMini
    product_unit: UnitMini