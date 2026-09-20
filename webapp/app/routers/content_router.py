"""
routers/content_router.py
----------------------------
Foydalanuvchi video yuklaydi -> fonda (background task) 1-3-bosqich
pipeline'i ishga tushadi (video formatlash, subtitr, AI caption, va
xohlasa Instagram'ga joylash) -> natija ContentJob orqali kuzatiladi.

Bu yerda ikkita muhim tekshiruv bor:
    1. Agar publish=true bo'lsa, foydalanuvchi avval Instagram akkauntini
       ulagan bo'lishi kerak (/instagram/connect)
    2. Foydalanuvchining FAOL OBUNASI bo'lishi shart — bu butun platformaning
       pul ishlash nuqtasi: to'lov qilmagan foydalanuvchi kontent yarata olmaydi
"""

import os
import sys
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from .. import models, auth
from ..database import get_db, SessionLocal

# ai-content-agent/ ildiz papkasini import yo'liga qo'shamiz — shu yerda
# main.py, video_processor.py va boshqa 1-3-bosqich skriptlari joylashgan
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

router = APIRouter(prefix="/content", tags=["content"])

UPLOAD_DIR = os.environ.get("CONTENT_UPLOAD_DIR", "uploads")


def _has_active_subscription(db: Session, user_id: int) -> bool:
    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == user_id,
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
            models.Subscription.end_date >= datetime.utcnow(),
        )
        .first()
    )
    return sub is not None


def _run_job(
    job_id: int,
    video_path: str,
    niche: str,
    language: str,
    publish: bool,
    ig_access_token: str | None,
    ig_user_id: str | None,
) -> None:
    """Fonda ishlaydigan vazifa — bu funksiya BackgroundTasks orqali chaqiriladi."""
    from main import run_pipeline  # lazy import: faqat haqiqatan kerak bo'lganda

    db = SessionLocal()
    try:
        job = db.query(models.ContentJob).filter(models.ContentJob.id == job_id).first()
        job.status = "processing"
        db.commit()

        try:
            result = run_pipeline(
                input_video=video_path,
                output_dir=os.path.join(UPLOAD_DIR, "output", str(job_id)),
                niche=niche,
                language=language,
                publish=publish,
                ig_access_token=ig_access_token,
                ig_user_id=ig_user_id,
            )
            job.status = "done"
            job.result_media_id = result.get("instagram_media_id")
            job.result_caption = result["caption_data"]["caption"]
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
        finally:
            job.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/upload-and-publish")
async def upload_and_publish(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    niche: str = Form("shaxsiy brend"),
    language: str = Form("uz"),
    publish: bool = Form(False),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_active_subscription(db, current_user.id):
        raise HTTPException(
            status_code=402,
            detail="Faol obuna topilmadi. Avval /subscribe orqali tarif tanlab to'lov qiling.",
        )

    ig_access_token = None
    ig_user_id = None
    if publish:
        account = (
            db.query(models.InstagramAccount)
            .filter(models.InstagramAccount.user_id == current_user.id)
            .first()
        )
        if not account:
            raise HTTPException(
                status_code=400,
                detail="Avval Instagram akkauntingizni ulang (GET /instagram/connect)",
            )
        ig_access_token = account.access_token
        ig_user_id = account.ig_user_id

    user_upload_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    video_path = os.path.join(user_upload_dir, file.filename)
    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = models.ContentJob(
        user_id=current_user.id,
        status="pending",
        input_filename=file.filename,
        niche=niche,
        language=language,
        publish_to_instagram=publish,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_job, job.id, video_path, niche, language, publish, ig_access_token, ig_user_id
    )

    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(models.ContentJob)
        .filter(models.ContentJob.id == job_id, models.ContentJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Ish topilmadi")

    return {
        "id": job.id,
        "status": job.status,
        "input_filename": job.input_filename,
        "result_media_id": job.result_media_id,
        "result_caption": job.result_caption,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.get("/jobs")
def list_jobs(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(models.ContentJob)
        .filter(models.ContentJob.user_id == current_user.id)
        .order_by(models.ContentJob.created_at.desc())
        .all()
    )
    return [
        {"id": j.id, "status": j.status, "input_filename": j.input_filename, "created_at": j.created_at}
        for j in jobs
    ]
