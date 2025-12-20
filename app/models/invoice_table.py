from uuid import uuid4
from sqlalchemy import Column,String,DateTime,func,Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum

class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    sold_by_name = Column(String(100), nullable=True)
    # sold_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    status = Column(SAEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    items = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )
