from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.product_table import ProductStatus, ProductType


class ProductBase(BaseModel):
    # Stable internal identifier you control (better than relying on name).
    sku: str
    
    # Human-friendly product name; used for search & display.
    name: str
    
    # Optional metadata (often missing in CSV imports).
    brand_name: Optional[str] = None
    supplier_name: Optional[str] = None
    barcode: Optional[str] = None

    # Pricing rule input (optional until you build pricing/cost flow).
    markup_percent: Optional[float] = None

    # Inventory alert threshold. 0 means "don't warn yet" until configured.
    reorder_level: int = 0

    # Category/type for filtering and rules.
    product_type: ProductType = ProductType.NON_MEDICAL

    # Compliance/business rule (OTC vs Rx).
    dispense_without_prescription: bool = True

    # Free-text policy notes.
    return_policy: Optional[str] = None

    # Soft state (active/inactive/discontinued) without deleting history.
    status: ProductStatus = ProductStatus.ACTIVE


class CreateProduct(ProductBase):

    # Intentionally no quantity_on_hand here:
    # Stock should start at 0 and be changed only via stock adjustments.
    pass

class ReadProduct(ProductBase):

    model_config = {"from_attributes": True}
    id: str
    quantity_on_hand: int
    created_at: datetime
    updated_at: datetime

class UpdateProduct(BaseModel):

    name: Optional[str] = None

    brand_name: Optional[str] = None
    supplier_name: Optional[str] = None
    barcode: Optional[str] = None

    markup_percent: Optional[float] = None
    reorder_level: Optional[int] = None
    product_type: Optional[ProductType] = None
    
    dispense_without_prescription: Optional[bool] = None
    return_policy: Optional[str] = None
    status: Optional[ProductStatus] = None


