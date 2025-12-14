from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


# Why stock changed (audit trail).
class StockAdjustmentReason(str, Enum):
    INITIAL_IMPORT = "INITIAL_IMPORT"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"


# Audit table: every change to stock is recorded here.
class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)

    change_qty = Column(Integer, nullable=False)
    reason = Column(SAEnum(StockAdjustmentReason), nullable=False)

    reference = Column(String(255), nullable=True)
    note = Column(String(255), nullable=True)
    created_by_user_id = Column(String(36), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Many-to-one relationship: each adjustment belongs to exactly one Product.
    # `back_populates` must match the attribute name on the other model.
    product = relationship("Product", back_populates="adjustments")
