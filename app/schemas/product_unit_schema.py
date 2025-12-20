from pydantic import BaseModel

from app.models.product_unit_table import BaseUnit


class ReadProductUnit(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    product_id: str
    name: BaseUnit
    multiplier_to_base: int
    price_per_unit: float
    is_default: bool
