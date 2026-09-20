"""
routers/subscription_router.py
---------------------------------
Tarif rejalarini ko'rsatish va obuna/to'lov jarayonini boshlash.
"""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..billing_links import generate_payme_link, generate_click_link

router = APIRouter(tags=["subscriptions"])


@router.get("/plans", response_model=list[schemas.PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.query(models.Plan).filter(models.Plan.is_active == True).all()  # noqa: E712


@router.post("/subscribe")
def subscribe(
    request: schemas.SubscribeRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(models.Plan).filter(models.Plan.id == request.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Tarif rejasi topilmadi")

    if request.provider not in ("payme", "click"):
        raise HTTPException(status_code=400, detail="provider 'payme' yoki 'click' bo'lishi kerak")

    subscription = models.Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status=models.SubscriptionStatus.PENDING,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # To'lovdan keyin foydalanuvchi ilovaga qaytishi uchun (ixtiyoriy — sozlanmasa
    # Payme/Click o'z standart "muvaffaqiyatli" sahifasida qoldiradi)
    frontend_url = os.environ.get("FRONTEND_BASE_URL")
    return_url = f"{frontend_url.rstrip('/')}/app/" if frontend_url else None

    if request.provider == "payme":
        payment_url = generate_payme_link(subscription.id, plan.price_uzs, return_url=return_url)
    else:
        payment_url = generate_click_link(subscription.id, plan.price_uzs, return_url=return_url)

    return {
        "subscription_id": subscription.id,
        "plan": plan.name,
        "amount_uzs": plan.price_uzs,
        "payment_url": payment_url,
    }


@router.get("/subscriptions/me", response_model=list[schemas.SubscriptionOut])
def my_subscriptions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == current_user.id)
        .order_by(models.Subscription.created_at.desc())
        .all()
    )



@router.get("/subscriptions/me", response_model=list[schemas.SubscriptionOut])
def my_subscriptions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == current_user.id)
        .order_by(models.Subscription.created_at.desc())
        .all()
    )
