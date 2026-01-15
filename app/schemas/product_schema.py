from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.models.product_table import ProductStatus, ProductType
from app.models.product_unit_table import BaseUnit
from app.schemas.product_unit_schema import ReadProductUnit

class ProductBase(BaseModel):
    
    # Human-friendly product name; used for search & display.
    name: str
    
    # Optional metadata (often missing in CSV imports).
    brand_name: str | None = None
    supplier_name: str | None = None
    barcode: str | None = None

    # Pricing rule input (optional until you build pricing/cost flow).
    markup_percent: float | None = None

    # Inventory alert threshold. 0 means "don't warn yet" until configured.
    reorder_level: int = 0

    # Category/type for filtering and rules.
    product_type: ProductType = ProductType.NON_MEDICAL

    # Compliance/business rule (OTC vs Rx).
    dispense_without_prescription: bool = True

    # Free-text policy notes.
    return_policy: str | None = None

    # Soft state (active/inactive/discontinued) without deleting history.
    status: ProductStatus = ProductStatus.ACTIVE
    deleted_at: datetime | None = Field(default=None)


class CreateProduct(ProductBase):
    # Base unit for the product
    base_unit: BaseUnit
    # Default unit price
    price_per_unit: float
    # Multiplier to convert this unit to base unit
    multiplier_to_base: float
    # Initial stock (optional, defaults to 0)
    initial_quantity: int = 0

class ReadProduct(ProductBase):

    model_config = {"from_attributes": True}
    id: str
    sku: str
    quantity_on_hand: int
    created_at: datetime
    updated_at: datetime
    product_units: List[ReadProductUnit]



class UpdateProduct(BaseModel):

    name: str | None = None
    sku: str | None = None
    brand_name: str | None = None
    supplier_name: str | None = None
    barcode: str | None = None

    markup_percent: float | None = None
    reorder_level: int | None = None
    product_type: ProductType | None = None
    
    dispense_without_prescription: bool | None = None
    return_policy: str | None = None
    status: ProductStatus | None = None
    deleted_at: datetime | None = None

