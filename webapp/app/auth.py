"""
auth.py
---------
Parol xeshlash (bcrypt to'g'ridan-to'g'ri) va JWT token yaratish/tekshirish.

Eslatma: passlib emas, bcrypt kutubxonasi bevosita ishlatiladi — passlib'ning
yangi bcrypt versiyalari bilan mos kelmaslik muammosi (versiya aniqlash xatosi)
tufayli bu ancha barqaror yechim.

MUHIM: SECRET_KEY production'da albatta environment o'zgaruvchi orqali
sozlanishi kerak (kodga yozib qo'yilmasin). Bu yerdagi standart qiymat
faqat lokal sinov uchun.
"""

import os
import bcrypt
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 kun

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    # bcrypt 72 baytdan uzun parollarni qabul qilmaydi — xavfsiz tomondan kesamiz
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    user_id = decode_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kirish ma'lumotlari noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi")
    return user


def get_current_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Faqat admin (saytga birinchi ro'yxatdan o'tgan egasi) kira oladigan endpointlar uchun."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu bo'lim faqat admin uchun")
    return current_user


def decode_user_id(token: str) -> int | None:
    """
    JWT'dan user_id ni ajratib oladi. get_current_user FastAPI dependency
    sifatida faqat Authorization header orqali ishlaydi; bu funksiya esa
    token istalgan joydan (masalan, OAuth redirect'dagi state parametridan)
    kelganda ham ishlatish uchun alohida ajratilgan.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except (JWTError, ValueError, TypeError):
        return None
