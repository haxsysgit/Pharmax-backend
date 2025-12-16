from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


# High-level classification for your CSV TYPE column.
class ProductType(str, Enum):
    MEDICAL = "Medical"
    NON_MEDICAL = "Non-medical"


class ProductStatus(str, Enum):
    ACTIVE = "Active"
    PENDING = "Pending"
    INACTIVE = "Inactive"


# Main inventory item table.
class Product(Base):
    __tablename__ = "products"

    # Primary key (UUID stored as string for SQLite simplicity).
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Human-friendly code you generate (unique).
    sku = Column(String(255), nullable=False, unique=True, index=True)

    # Product name; indexed for fast search in the invoice flow.
    name = Column(String(255), nullable=False, index=True)

    # Optional metadata (your CSV often has blanks here).
    brand_name = Column(String(255), nullable=True)
    supplier_name = Column(String(255), nullable=True)
    barcode = Column(String(255), nullable=True, index=True)
    markup_percent = Column(Float, nullable=True)

    # Current stock snapshot (fast to read).
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=0)
    product_type = Column(SAEnum(ProductType), nullable=False)
    dispense_without_prescription = Column(Boolean, nullable=False, default=True)
    return_policy = Column(String(255), nullable=True)
    status = Column(SAEnum(ProductStatus), nullable=False, default=ProductStatus.ACTIVE)

    # Timestamps (created_at set by DB; updated_at auto-updates on change).
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # One-to-many relationship: one Product has many StockAdjustment rows.
    # `back_populates` must match the attribute name on the other model.
    # `cascade` controls what happens to adjustments when you operate on Product.
    adjustments = relationship(
        "StockAdjustment", back_populates="product", cascade="all, delete-orphan"
    )
