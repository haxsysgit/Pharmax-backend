from pydantic import BaseModel, Field


class AddInvoiceItem(BaseModel):
    product_id: str
    product_unit_id: str
    quantity: int = Field(ge=1)
    unit_price: float | None = None

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
    product: ProductMini | None = None
    product_unit: UnitMini | None = None