from sqlalchemy import String, Boolean, DateTime
from app.db.base import Base
from sqlalchemy import func,Enum as SAEnum
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import relationship

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CASHIER = "CASHIER"
    SALES = "SALES"



class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        nullable=False,
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")
    adjustments = relationship("StockAdjustment", back_populates="user")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())