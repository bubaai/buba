"""
routers/admin_router.py
--------------------------
Admin panel: saytga birinchi ro'yxatdan o'tgan egasi (siz) uchun —
barcha foydalanuvchilar, obunalar, to'lovlar va tarif narxlarini
boshqarish. Faqat is_admin=True bo'lgan hisob kira oladi.
"""

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, auth
from ..database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def get_stats(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Umumiy ko'rsatkichlar: foydalanuvchilar, faol obunalar, jami va oylik tushum."""
    total_users = db.query(models.User).count()

    active_subscriptions = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
            models.Subscription.end_date >= datetime.utcnow(),
        )
        .count()
    )

    total_revenue = (
        db.query(func.sum(models.Transaction.amount))
        .filter(models.Transaction.state == models.TransactionState.PERFORMED)
        .scalar()
    ) or 0

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_this_month = (
        db.query(func.sum(models.Transaction.amount))
        .filter(
            models.Transaction.state == models.TransactionState.PERFORMED,
            models.Transaction.performed_at >= month_start,
        )
        .scalar()
    ) or 0

    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "total_revenue_uzs": total_revenue,
        "revenue_this_month_uzs": revenue_this_month,
    }


@router.get("/users")
def list_users(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Har bir foydalanuvchi va uning joriy obuna holati."""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    result = []
    for u in users:
        active_sub = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.user_id == u.id,
                models.Subscription.status == models.SubscriptionStatus.ACTIVE,
                models.Subscription.end_date >= datetime.utcnow(),
            )
            .first()
        )
        result.append(
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_admin": u.is_admin,
                "created_at": u.created_at,
                "subscription_status": active_sub.status.value if active_sub else "yo'q",
                "subscription_end_date": active_sub.end_date if active_sub else None,
            }
        )
    return result


@router.get("/subscriptions")
def list_subscriptions(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Barcha obunalar (foydalanuvchi va tarif nomi bilan)."""
    subs = db.query(models.Subscription).order_by(models.Subscription.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "user_email": s.user.email,
            "plan_name": s.plan.name,
            "status": s.status.value,
            "start_date": s.start_date,
            "end_date": s.end_date,
            "created_at": s.created_at,
        }
        for s in subs
    ]


@router.get("/transactions")
def list_transactions(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Barcha to'lov tranzaksiyalari — kim, qachon, qancha to'lagani."""
    txns = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "user_email": t.subscription.user.email,
            "plan_name": t.subscription.plan.name,
            "provider": t.provider.value,
            "amount_uzs": t.amount,
            "state": t.state.value,
            "created_at": t.created_at,
            "performed_at": t.performed_at,
        }
        for t in txns
    ]


@router.get("/plans")
def list_all_plans(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Barcha tariflar, jumladan faol bo'lmaganlari ham (admin uchun to'liq ro'yxat)."""
    plans = db.query(models.Plan).order_by(models.Plan.id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price_uzs": p.price_uzs,
            "duration_days": p.duration_days,
            "is_active": p.is_active,
        }
        for p in plans
    ]


@router.post("/plans")
def create_plan(
    name: str,
    price_uzs: float,
    duration_days: int = 30,
    description: str | None = None,
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Yangi tarif rejasi yaratadi."""
    plan = models.Plan(
        name=name, price_uzs=price_uzs, duration_days=duration_days,
        description=description, is_active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"id": plan.id, "name": plan.name, "price_uzs": plan.price_uzs}


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    name: str | None = None,
    price_uzs: float | None = None,
    duration_days: int | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Mavjud tarif narxi/muddati/nomi/holatini o'zgartiradi (faqat berilgan maydonlar)."""
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Tarif topilmadi")

    if name is not None:
        plan.name = name
    if price_uzs is not None:
        plan.price_uzs = price_uzs
    if duration_days is not None:
        plan.duration_days = duration_days
    if description is not None:
        plan.description = description
    if is_active is not None:
        plan.is_active = is_active

    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "name": plan.name, "price_uzs": plan.price_uzs,
        "duration_days": plan.duration_days, "is_active": plan.is_active,
    }


@router.post("/self-test-subscription")
def grant_self_test_subscription(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """
    FAQAT ADMIN (siz) UCHUN: Payme/Click haqiqiy kalitlari hali sozlanmagan
    bo'lsa ham, saytni sinash imkoni bo'lishi uchun o'zingizga to'lovsiz,
    365 kunlik sinov obunasini beradi. Haqiqiy mijozlar bu tugmani ko'rmaydi —
    ular /subscribe orqali, haqiqiy to'lov qilib obuna oladi.
    """
    plan = db.query(models.Plan).filter(models.Plan.is_active == True).first()  # noqa: E712
    if not plan:
        raise HTTPException(status_code=404, detail="Faol tarif topilmadi — avval tarif qo'shing")

    existing = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == admin.id,
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
        )
        .first()
    )
    if existing:
        existing.end_date = datetime.utcnow() + timedelta(days=365)
    else:
        sub = models.Subscription(
            user_id=admin.id,
            plan_id=plan.id,
            status=models.SubscriptionStatus.ACTIVE,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=365),
        )
        db.add(sub)

    db.commit()
    return {"status": "ok", "plan": plan.name}


@router.post("/self-test-instagram")
def link_self_test_instagram(
    admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """
    FAQAT ADMIN (siz) UCHUN: to'liq Instagram OAuth (redirect URI Meta'da
    ro'yxatdan o'tishi kerak) hali sozlanmagan bo'lsa ham, serverda saqlangan
    IG_ACCESS_TOKEN/IG_USER_ID orqali o'zingizga Instagram akkauntini ulaydi.
    Haqiqiy mijozlar buni ko'rmaydi — ular "Instagram ulash" tugmasi orqali
    o'z akkauntini OAuth bilan ulaydi.
    """
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = os.environ.get("IG_USER_ID")
    if not access_token or not ig_user_id:
        raise HTTPException(
            status_code=400,
            detail="Serverda IG_ACCESS_TOKEN yoki IG_USER_ID sozlanmagan",
        )

    account = (
        db.query(models.InstagramAccount)
        .filter(models.InstagramAccount.user_id == admin.id)
        .first()
    )
    if account:
        account.access_token = access_token
        account.ig_user_id = ig_user_id
        account.connected_at = datetime.utcnow()
    else:
        account = models.InstagramAccount(
            user_id=admin.id,
            ig_user_id=ig_user_id,
            access_token=access_token,
            username="buba_smm",
        )
        db.add(account)

    db.commit()
    return {"status": "ok", "username": account.username}
