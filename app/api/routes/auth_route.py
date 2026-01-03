from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import Token, create_access_token
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.user_schema import LoginUser, RegisterUser, UserRead
from app.services.user_service import UserService


router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user: RegisterUser, db: Session = Depends(get_db)):
    try:
        created = UserService.register_user(db, user)
    except ValueError as exc:
        # Map our specific conflict signal to a 400; re-raise anything else
        if str(exc) == "username or email taken":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered") from exc
        raise

    return created


@router.post("/token", response_model=Token)
def form_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm provides form-encoded username & password fields.
    # We treat `username` as our identifier (username or email).
    authenticated = UserService.authenticate(db, form_data.username, form_data.password)
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials",
        )

    access_token = create_access_token({"sub": authenticated.id, "role": authenticated.role.value})
    return Token(access_token=access_token, token_type="bearer")

@router.post("/login",response_model=Token)
def login(user: LoginUser, db: Session = Depends(get_db)):
    authenticated = UserService.authenticate(db, user.identifier,user.password)

    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authentication credentials")
    
    access_token = create_access_token({"sub": authenticated.id, "role": authenticated.role.value})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
def read_me(current_user = Depends(get_current_user)):
    return current_user


@router.get("/ping")
def ping():
    return {"status": "ok"}
