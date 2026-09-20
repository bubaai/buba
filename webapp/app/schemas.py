"""
schemas.py
------------
API so'rov/javob shakllarini belgilaydi (Pydantic orqali).
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PlanOut(BaseModel):
    id: int
    name: str
    description: str | None
    price_uzs: float
    duration_days: int

    class Config:
        from_attributes = True


class SubscribeRequest(BaseModel):
    plan_id: int
    provider: str  # "payme" yoki "click"


class SubscriptionOut(BaseModel):
    id: int
    plan_id: int
    status: str
    start_date: datetime | None
    end_date: datetime | None

    class Config:
        from_attributes = True
