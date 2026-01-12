from pydantic import BaseModel

from app.models.product_unit_table import BaseUnit


class CreateProductUnit(BaseModel):
    unit: BaseUnit
    price_per_unit: float
    multiplier_to_base: float


class ReadProductUnit(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    unit: BaseUnit
    price_per_unit: float
    multiplier_to_base: float
