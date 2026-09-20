"""
routers/auth_router.py
-------------------------
Ro'yxatdan o'tish va kirish endpointlari.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu email allaqachon ro'yxatdan o'tgan")

    # Saytga birinchi bo'lib ro'yxatdan o'tgan kishi — egasi (admin) hisoblanadi
    is_first_user = db.query(models.User).count() == 0

    user = models.User(
        email=user_in.email,
        hashed_password=auth.hash_password(user_in.password),
        full_name=user_in.full_name,
        is_admin=is_first_user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email yoki parol noto'g'ri")

    token = auth.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user
