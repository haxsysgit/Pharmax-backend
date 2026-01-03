from sqlalchemy.orm import Session
from app.models.audit_log_table import AuditLog
from typing import Optional, Dict, Any
import json


class AuditService:
    @staticmethod
    def log_action( db: Session, user_id: str,action: str,
                resource_type: str,resource_id: Optional[str] = None,
                details: Optional[Dict[str, Any]] = None
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
