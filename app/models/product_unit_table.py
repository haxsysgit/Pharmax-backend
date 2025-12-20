from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class BaseUnit(str, Enum):
    TABLET = "Tablet"
    CAPSULE = "Capsule"
    SACHET = "Sachet"
    PACK = "Pack"
    BOTTLE = "Bottle"
    VIAL = "Vial"
    AMPOULE = "Ampoule"
    TUBE = "Tube"
    CREAM = "Cream"
    OINTMENT = "Ointment"
    GEL = "Gel"
    SYRUP = "Syrup"
    SUSPENSION = "Suspension"
    DROPS = "Drops"
    POWDER = "Powder"
    BOX = "Box"
    STRIP = "Strip"
    CARTON = "Carton"
    CONTAINER = "Container"


class ProductUnit(Base):
    __tablename__ = "product_units"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)

    name = Column(SAEnum(BaseUnit), nullable=False)
    multiplier_to_base = Column(Integer, nullable=False, default=1)
    price_per_unit = Column(Float, nullable=False, default=0.0)
    is_default = Column(Boolean, nullable=False, default=False)

    product = relationship("Product", back_populates="product_units")