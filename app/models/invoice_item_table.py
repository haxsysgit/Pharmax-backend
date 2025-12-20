from uuid import uuid4
from sqlalchemy import Column,Float,Integer,String,ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base



class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    product_unit_id = Column(String(36), ForeignKey("product_units.id"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
    product_unit = relationship("ProductUnit")
    
    