"""
models.py
-----------
Ko'p mijozli (multi-tenant) platforma uchun ma'lumotlar bazasi jadvallari.

Jadvallar:
    User             — har bir mijoz (obunachi)
    Plan             — mavjud tarif rejalari (narx, muddat)
    Subscription     — foydalanuvchining faol/tugagan obunasi
    Transaction      — Payme/Click orqali to'lov tranzaksiyalari
    InstagramAccount — foydalanuvchi ulagan Instagram akkaunti (token bilan)
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship

from .database import Base


class SubscriptionStatus(str, enum.Enum):
    PENDING = "pending"      # to'lov kutilmoqda
    ACTIVE = "active"        # to'langan, faol
    EXPIRED = "expired"      # muddati tugagan
    CANCELLED = "cancelled"  # bekor qilingan


class TransactionState(str, enum.Enum):
    CREATED = "created"        # Payme: CreateTransaction bosqichi
    PERFORMED = "performed"    # to'lov muvaffaqiyatli yakunlandi
    CANCELLED = "cancelled"    # bekor qilindi / xato


class PaymentProvider(str, enum.Enum):
    PAYME = "payme"
    CLICK = "click"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    instagram_accounts = relationship("InstagramAccount", back_populates="user")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_uzs = Column(Float, nullable=False)   # so'mda, masalan 299000.0
    duration_days = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan")
    transactions = relationship("Transaction", back_populates="subscription")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    provider = Column(Enum(PaymentProvider), nullable=False)
    provider_transaction_id = Column(String(255), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    state = Column(Enum(TransactionState), default=TransactionState.CREATED)
    created_at = Column(DateTime, default=datetime.utcnow)
    performed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(255), nullable=True)

    # Click uchun qo'shimcha maydon (Complete bosqichida kerak bo'ladi)
    click_prepare_id = Column(String(255), nullable=True)

    subscription = relationship("Subscription", back_populates="transactions")


class ContentJob(Base):
    """
    Foydalanuvchi video yuklab, pipeline'ni ishga tushirganda yaratiladigan
    ish (job). Video ishlov + AI caption + (ixtiyoriy) Instagram'ga joylash
    fonda (background task) bajariladi — bu jadval uning holatini kuzatadi.
    """
    __tablename__ = "content_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending -> processing -> done / failed
    input_filename = Column(String(500), nullable=True)
    niche = Column(String(255), nullable=True)
    language = Column(String(10), default="uz")
    publish_to_instagram = Column(Boolean, default=False)
    result_media_id = Column(String(255), nullable=True)
    result_caption = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ig_user_id = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)  # Eslatma: real productionda shifrlab saqlash tavsiya etiladi
    username = Column(String(255), nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="instagram_accounts")
