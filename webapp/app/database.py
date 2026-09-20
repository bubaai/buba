"""
database.py
-------------
SQLAlchemy ulanishi. MVP uchun SQLite ishlatiladi — alohida server
o'rnatish shart emas, hammasi bitta faylda (webapp.db).

Real ishlab chiqarish (production) uchun tavsiya: PostgreSQL'ga
o'tish — DATABASE_URL environment o'zgaruvchisini
"postgresql://user:pass@host/dbname" ga o'zgartirish kifoya,
qolgan kod o'zgarishsiz ishlaydi (SQLAlchemy orqali).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./webapp.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: har bir so'rov uchun DB sessiyasi ochib, oxirida yopadi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Jadvallarni yaratadi (agar mavjud bo'lmasa). Ilova ishga tushganda chaqiriladi."""
    from . import models  # noqa: F401 - modellarni ro'yxatdan o'tkazish uchun import qilinadi
    Base.metadata.create_all(bind=engine)
