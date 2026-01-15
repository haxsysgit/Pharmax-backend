from sqlalchemy.orm import Session
from app.models.audit_log_table import AuditLog
from typing import Dict, Any
import json
from sqlalchemy import select


class AuditService:
    @staticmethod
    def log_action( db: Session, user_id: str,action: str,
                resource_type: str,resource_id: str | None = None,
                details: Dict[str, Any] | None = None
                ) -> AuditLog:


        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
        )

        db.add(audit_log)
        return audit_log
