from pydantic import BaseModel, constr
from app.models.user_table import UserRole
from datetime import datetime

class UserBase(BaseModel):
    username: constr(max_length=72)
    email: constr(max_length=72)
    full_name: str | None = None
    role: UserRole


class RegisterUser(UserBase):
    password: constr(min_length=8, max_length=72)

class LoginUser(BaseModel):
    identifier: constr(max_length=72)
    password: constr(min_length=8, max_length=72)

class UserRead(UserBase):
    model_config = {"from_attributes": True}

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


