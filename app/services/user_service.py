from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user_table import User
from app.schemas.user_schema import RegisterUser
from app.services.audit_service import AuditService


class UserService:
    """User-related business logic (registration, authentication)."""

    @staticmethod
    def register_user(db: Session, payload: RegisterUser) -> User:
        """Create a new user after enforcing username/email uniqueness."""

        stmt = select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
        existing = db.execute(stmt).scalar_one_or_none()

        if existing:
            # Let the route decide exact HTTP response; here we just signal conflict
            raise ValueError("username or email taken")

        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            hashed_password=get_password_hash(payload.password),
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log user creation after getting the ID
        AuditService.log_action(db=db, 
                                user_id=user.id,
                                action="CREATE",
                                resource_type="USER",
                                resource_id=user.id,
                                details={"username": user.username, "email": user.email, "role": user.role}
                                )
        return user

    @staticmethod
    def authenticate(db: Session, identifier: str, password: str) -> User | None:
        """Return user if identifier (username or email) + password are valid."""

        stmt = select(User).where(
            or_(User.username == identifier, User.email == identifier)
        )
        user = db.execute(stmt).scalar_one_or_none()

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        AuditService.log_action(db=db, 
                        user_id=user.id,
                        action="LOGIN",
                        resource_type="User",
                        resource_id=user.id,
                        details={"identifier": identifier, "role": user.role}
                        )
        return user
