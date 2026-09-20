"""
routers/payme_router.py
--------------------------
Payme Merchant API protokoli (JSON-RPC 2.0). Payme foydalanuvchi to'lovni
checkout sahifasida tasdiqlagach, shu endpoint'ga ketma-ket so'rovlar
yuboradi: CheckPerformTransaction -> CreateTransaction -> PerformTransaction
(yoki xato bo'lsa CancelTransaction).

Rasmiy hujjat: https://developer.help.paycom.uz/protokol-merchant-api/

MUHIM: Bu implementatsiya Payme'ning rasmiy hujjatiga asoslangan, lekin
haqiqiy Payme test muhitida (checkup tool) hali sinalmagan — production'ga
chiqarishdan oldin Payme Business kabinetidagi "Checkup" vositasi orqali
albatta tekshiring.
"""

import os
import base64
import time as time_module
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal

router = APIRouter(prefix="/payments/payme", tags=["payme"])

# Payme xato kodlari (rasmiy protokol bo'yicha)
ERROR_INVALID_AUTH = -32504
ERROR_ACCOUNT_NOT_FOUND = -31050
ERROR_INCORRECT_AMOUNT = -31001
ERROR_TRANSACTION_NOT_FOUND = -31003
ERROR_CANNOT_PERFORM = -31008
ERROR_METHOD_NOT_FOUND = -32601


def _now_ms() -> int:
    return int(time_module.time() * 1000)


def _rpc_result(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": {"ru": message, "uz": message, "en": message}},
    }


def _check_auth(authorization: str | None) -> bool:
    """Payme so'rovlari Basic Auth bilan keladi: login='Paycom', parol=PAYME_KEY."""
    merchant_key = os.environ.get("PAYME_KEY")
    if not merchant_key or not authorization or not authorization.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(authorization[6:]).decode()
        login, _, password = decoded.partition(":")
        return login == "Paycom" and password == merchant_key
    except Exception:
        return False


@router.post("")
async def payme_webhook(request: Request, authorization: str | None = Header(default=None)):
    body = await request.json()
    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if not _check_auth(authorization):
        return JSONResponse(_rpc_error(request_id, ERROR_INVALID_AUTH, "Avtorizatsiya xato"))

    db: Session = SessionLocal()
    try:
        if method == "CheckPerformTransaction":
            return JSONResponse(_handle_check_perform(db, request_id, params))
        elif method == "CreateTransaction":
            return JSONResponse(_handle_create(db, request_id, params))
        elif method == "PerformTransaction":
            return JSONResponse(_handle_perform(db, request_id, params))
        elif method == "CancelTransaction":
            return JSONResponse(_handle_cancel(db, request_id, params))
        elif method == "CheckTransaction":
            return JSONResponse(_handle_check_transaction(db, request_id, params))
        elif method == "GetStatement":
            return JSONResponse(_handle_get_statement(db, request_id, params))
        else:
            return JSONResponse(_rpc_error(request_id, ERROR_METHOD_NOT_FOUND, "Metod topilmadi"))
    finally:
        db.close()


def _find_subscription(db: Session, params: dict):
    account = params.get("account", {})
    subscription_id = account.get("subscription_id")
    if not subscription_id:
        return None
    return db.query(models.Subscription).filter(models.Subscription.id == int(subscription_id)).first()


def _handle_check_perform(db: Session, request_id, params: dict) -> dict:
    subscription = _find_subscription(db, params)
    if not subscription:
        return _rpc_error(request_id, ERROR_ACCOUNT_NOT_FOUND, "Obuna topilmadi")

    expected_amount = int(round(subscription.plan.price_uzs * 100))
    if int(params.get("amount", 0)) != expected_amount:
        return _rpc_error(request_id, ERROR_INCORRECT_AMOUNT, "Summa noto'g'ri")

    return _rpc_result(request_id, {"allow": True})


def _handle_create(db: Session, request_id, params: dict) -> dict:
    payme_txn_id = params.get("id")

    existing = (
        db.query(models.Transaction)
        .filter(models.Transaction.provider_transaction_id == payme_txn_id)
        .first()
    )
    if existing:
        return _rpc_result(
            request_id,
            {
                "create_time": int(existing.created_at.timestamp() * 1000),
                "transaction": str(existing.id),
                "state": 1 if existing.state == models.TransactionState.CREATED else 2,
            },
        )

    subscription = _find_subscription(db, params)
    if not subscription:
        return _rpc_error(request_id, ERROR_ACCOUNT_NOT_FOUND, "Obuna topilmadi")

    expected_amount = int(round(subscription.plan.price_uzs * 100))
    if int(params.get("amount", 0)) != expected_amount:
        return _rpc_error(request_id, ERROR_INCORRECT_AMOUNT, "Summa noto'g'ri")

    txn = models.Transaction(
        subscription_id=subscription.id,
        provider=models.PaymentProvider.PAYME,
        provider_transaction_id=payme_txn_id,
        amount=params.get("amount", 0) / 100,
        state=models.TransactionState.CREATED,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return _rpc_result(
        request_id,
        {
            "create_time": int(txn.created_at.timestamp() * 1000),
            "transaction": str(txn.id),
            "state": 1,
        },
    )


def _handle_perform(db: Session, request_id, params: dict) -> dict:
    payme_txn_id = params.get("id")
    txn = (
        db.query(models.Transaction)
        .filter(models.Transaction.provider_transaction_id == payme_txn_id)
        .first()
    )
    if not txn:
        return _rpc_error(request_id, ERROR_TRANSACTION_NOT_FOUND, "Tranzaksiya topilmadi")

    if txn.state == models.TransactionState.PERFORMED:
        return _rpc_result(
            request_id,
            {"transaction": str(txn.id), "perform_time": int(txn.performed_at.timestamp() * 1000), "state": 2},
        )
    if txn.state == models.TransactionState.CANCELLED:
        return _rpc_error(request_id, ERROR_CANNOT_PERFORM, "Bekor qilingan tranzaksiyani bajarib bo'lmaydi")

    txn.state = models.TransactionState.PERFORMED
    txn.performed_at = datetime.utcnow()

    subscription = txn.subscription
    plan = subscription.plan
    subscription.status = models.SubscriptionStatus.ACTIVE
    subscription.start_date = datetime.utcnow()
    subscription.end_date = datetime.utcnow() + timedelta(days=plan.duration_days)

    db.commit()
    db.refresh(txn)

    return _rpc_result(
        request_id,
        {"transaction": str(txn.id), "perform_time": int(txn.performed_at.timestamp() * 1000), "state": 2},
    )


def _handle_cancel(db: Session, request_id, params: dict) -> dict:
    payme_txn_id = params.get("id")
    reason = params.get("reason")

    txn = (
        db.query(models.Transaction)
        .filter(models.Transaction.provider_transaction_id == payme_txn_id)
        .first()
    )
    if not txn:
        return _rpc_error(request_id, ERROR_TRANSACTION_NOT_FOUND, "Tranzaksiya topilmadi")

    was_performed = txn.state == models.TransactionState.PERFORMED

    if txn.state != models.TransactionState.CANCELLED:
        txn.state = models.TransactionState.CANCELLED
        txn.cancelled_at = datetime.utcnow()
        txn.cancel_reason = str(reason)

        if was_performed:
            txn.subscription.status = models.SubscriptionStatus.CANCELLED

        db.commit()
        db.refresh(txn)

    return _rpc_result(
        request_id,
        {
            "transaction": str(txn.id),
            "cancel_time": int(txn.cancelled_at.timestamp() * 1000),
            "state": -2 if was_performed else -1,
        },
    )


def _handle_check_transaction(db: Session, request_id, params: dict) -> dict:
    payme_txn_id = params.get("id")
    txn = (
        db.query(models.Transaction)
        .filter(models.Transaction.provider_transaction_id == payme_txn_id)
        .first()
    )
    if not txn:
        return _rpc_error(request_id, ERROR_TRANSACTION_NOT_FOUND, "Tranzaksiya topilmadi")

    state_map = {
        models.TransactionState.CREATED: 1,
        models.TransactionState.PERFORMED: 2,
        models.TransactionState.CANCELLED: -2 if txn.performed_at else -1,
    }

    return _rpc_result(
        request_id,
        {
            "create_time": int(txn.created_at.timestamp() * 1000),
            "perform_time": int(txn.performed_at.timestamp() * 1000) if txn.performed_at else 0,
            "cancel_time": int(txn.cancelled_at.timestamp() * 1000) if txn.cancelled_at else 0,
            "transaction": str(txn.id),
            "state": state_map[txn.state],
            "reason": txn.cancel_reason,
        },
    )


def _handle_get_statement(db: Session, request_id, params: dict) -> dict:
    from_ts = params.get("from", 0) / 1000
    to_ts = params.get("to", 0) / 1000

    txns = (
        db.query(models.Transaction)
        .filter(models.Transaction.provider == models.PaymentProvider.PAYME)
        .filter(models.Transaction.created_at >= datetime.utcfromtimestamp(from_ts))
        .filter(models.Transaction.created_at <= datetime.utcfromtimestamp(to_ts))
        .all()
    )

    state_map = {
        models.TransactionState.CREATED: 1,
        models.TransactionState.PERFORMED: 2,
        models.TransactionState.CANCELLED: -1,
    }

    transactions_list = [
        {
            "id": t.provider_transaction_id,
            "time": int(t.created_at.timestamp() * 1000),
            "amount": int(t.amount * 100),
            "account": {"subscription_id": str(t.subscription_id)},
            "create_time": int(t.created_at.timestamp() * 1000),
            "perform_time": int(t.performed_at.timestamp() * 1000) if t.performed_at else 0,
            "cancel_time": int(t.cancelled_at.timestamp() * 1000) if t.cancelled_at else 0,
            "transaction": str(t.id),
            "state": state_map[t.state],
        }
        for t in txns
    ]

    return _rpc_result(request_id, {"transactions": transactions_list})
