from app.db.base import Base
from sqlalchemy import String, DateTime, Text, ForeignKey,func,Index
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import json
from json import JSONDecodeError
from sqlalchemy.orm import relationship


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user = relationship(
        "User",
        back_populates="audit_logs",
        lazy="joined",  # good default for audit views
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action} "
            f"resource={self.resource_type}:{self.resource_id} "
            f"user={self.user_id} "
            f"at={self.created_at}>"
        )

    @property
    def details_dict(self) -> dict:
        if not self.details:
            return {}
        try:
            return json.loads(self.details)
        except (JSONDecodeError, TypeError):
            return {}

    @details_dict.setter
    def details_dict(self, value: dict | None):
        if value is None:
            self.details = None
        elif isinstance(value, dict):
            self.details = json.dumps(value)
        else:
            raise ValueError("details_dict must be a dict or None")

    @property
    def summary_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
