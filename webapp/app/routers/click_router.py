"""
routers/click_router.py
--------------------------
Click.uz Shop API protokoli. Ikki bosqichdan iborat: prepare (to'lovdan
oldin tekshirish) va complete (to'lov yakunlangach tasdiqlash). Har bir
so'rov MD5 imzo (sign_string) bilan keladi — buni albatta tekshirish shart,
aks holda soxta so'rovlar orqali "to'lov qilingan" deb aldash mumkin bo'ladi.

Rasmiy hujjat: https://docs.click.uz

MUHIM: Bu implementatsiya keng tarqalgan (community) Click integratsiyalari
asosida yozilgan, lekin haqiqiy Click test muhitida hali sinalmagan —
production'ga chiqarishdan oldin Click hamkor bilan birga sinov to'lovlari
orqali tekshiring.
"""

import os
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Form
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal

router = APIRouter(prefix="/payments/click", tags=["click"])

# Click xato kodlari
CLICK_ERROR_SUCCESS = 0
CLICK_ERROR_SIGN_FAILED = -1
CLICK_ERROR_AMOUNT = -2
CLICK_ERROR_ACTION_NOT_FOUND = -3
CLICK_ERROR_ALREADY_PAID = -4
CLICK_ERROR_USER_NOT_FOUND = -5
CLICK_ERROR_TRANSACTION_NOT_FOUND = -6
CLICK_ERROR_TRANSACTION_CANCELLED = -9


@router.post("/prepare")
async def click_prepare(
    click_trans_id: str = Form(...),
    service_id: str = Form(...),
    merchant_trans_id: str = Form(...),
    amount: str = Form(...),
    action: str = Form(...),
    sign_time: str = Form(...),
    sign_string: str = Form(...),
    error: str = Form(default="0"),
):
    # Imzo: md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id + amount + action + sign_time)
    raw = f"{click_trans_id}{service_id}{os.environ.get('CLICK_SECRET_KEY', '')}{merchant_trans_id}{amount}{action}{sign_time}"
    expected_sign = hashlib.md5(raw.encode()).hexdigest()

    if expected_sign != sign_string:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": CLICK_ERROR_SIGN_FAILED,
            "error_note": "Imzo noto'g'ri",
        }

    db: Session = SessionLocal()
    try:
        subscription = (
            db.query(models.Subscription)
            .filter(models.Subscription.id == int(merchant_trans_id))
            .first()
        )
        if not subscription:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": CLICK_ERROR_USER_NOT_FOUND,
                "error_note": "Obuna topilmadi",
            }

        expected_amount = subscription.plan.price_uzs
        if abs(float(amount) - expected_amount) > 0.01:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": CLICK_ERROR_AMOUNT,
                "error_note": "Summa mos emas",
            }

        existing = (
            db.query(models.Transaction)
            .filter(models.Transaction.provider_transaction_id == click_trans_id)
            .first()
        )
        if existing:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_prepare_id": existing.id,
                "error": CLICK_ERROR_SUCCESS,
                "error_note": "Success",
            }

        txn = models.Transaction(
            subscription_id=subscription.id,
            provider=models.PaymentProvider.CLICK,
            provider_transaction_id=click_trans_id,
            amount=float(amount),
            state=models.TransactionState.CREATED,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": txn.id,
            "error": CLICK_ERROR_SUCCESS,
            "error_note": "Success",
        }
    finally:
        db.close()


@router.post("/complete")
async def click_complete(
    click_trans_id: str = Form(...),
    service_id: str = Form(...),
    merchant_trans_id: str = Form(...),
    merchant_prepare_id: str = Form(...),
    amount: str = Form(...),
    action: str = Form(...),
    sign_time: str = Form(...),
    sign_string: str = Form(...),
    error: str = Form(default="0"),
):
    # Imzo: md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)
    raw = (
        f"{click_trans_id}{service_id}{os.environ.get('CLICK_SECRET_KEY', '')}"
        f"{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
    )
    expected_sign = hashlib.md5(raw.encode()).hexdigest()

    if expected_sign != sign_string:
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error": CLICK_ERROR_SIGN_FAILED,
            "error_note": "Imzo noto'g'ri",
        }

    db: Session = SessionLocal()
    try:
        txn = (
            db.query(models.Transaction)
            .filter(models.Transaction.provider_transaction_id == click_trans_id)
            .first()
        )
        if not txn:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": CLICK_ERROR_TRANSACTION_NOT_FOUND,
                "error_note": "Tranzaksiya topilmadi",
            }

        if txn.state == models.TransactionState.CANCELLED:
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": CLICK_ERROR_TRANSACTION_CANCELLED,
                "error_note": "Tranzaksiya bekor qilingan",
            }

        if int(error) < 0:
            # Click o'zi xato haqida xabar bergan — tranzaksiyani bekor qilamiz
            txn.state = models.TransactionState.CANCELLED
            txn.cancelled_at = datetime.utcnow()
            txn.cancel_reason = f"Click error: {error}"
            db.commit()
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error": CLICK_ERROR_SUCCESS,
                "error_note": "Bekor qilindi",
            }

        if txn.state != models.TransactionState.PERFORMED:
            txn.state = models.TransactionState.PERFORMED
            txn.performed_at = datetime.utcnow()

            subscription = txn.subscription
            plan = subscription.plan
            subscription.status = models.SubscriptionStatus.ACTIVE
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=plan.duration_days)

            db.commit()
            db.refresh(txn)

        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": txn.id,
            "error": CLICK_ERROR_SUCCESS,
            "error_note": "Success",
        }
    finally:
        db.close()
