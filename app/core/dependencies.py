from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Callable
from jose import JWTError

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user_table import User, UserRole


# OAuth2 password flow: the token endpoint is /auth/token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(db: Session = Depends(get_db),token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials")

    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user


def require_role(*roles: UserRole) -> Callable:
    """Return a dependency that ensures the current user has one of the given roles.

    Usage in routes:

        @router.delete("/...")
        def delete(..., current_user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if roles and current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return _dependency
