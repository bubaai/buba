"""
routers/instagram_router.py
------------------------------
Har bir foydalanuvchi o'zining Instagram professional akkauntini web
orqali ulashi uchun OAuth oqimi ("Business Login for Instagram").

Oqim:
    1. GET /instagram/connect  — foydalanuvchi bu yerga kirsa, Instagram
       ruxsat sahifasiga yo'naltiriladi (state=uning JWT tokeni, shuning
       uchun callback qaysi foydalanuvchi ekanini biladi)
    2. Instagram foydalanuvchidan ruxsat so'raydi, tasdiqlangач bizning
       redirect_uri'ga ?code=...&state=... bilan qaytaradi
    3. GET /instagram/callback — code'ni qisqa muddatli tokenga, so'ng
       uzoq muddatli (60 kunlik) tokenga almashtiradi, akkaunt ID va
       username'ni olib, InstagramAccount jadvaliga saqlaydi

Talab qilinadigan environment o'zgaruvchilar:
    IG_APP_ID        — Meta App Dashboard'dagi Instagram App ID
    IG_APP_SECRET     — Instagram App Secret
    IG_REDIRECT_URI   — Meta App'da ro'yxatdan o'tkazilgan qaytish manzili
                         (masalan https://sizning-domen.uz/instagram/callback)

MUHIM: Bu implementatsiya Meta'ning rasmiy hujjatiga asoslangan, lekin
haqiqiy Instagram OAuth serveri bilan hali sinalmagan (bu sandbox'da
instagram.com domeniga tarmoq ruxsati yo'q va haqiqiy App ID/Secret yo'q).
Ichki mantiq (state tekshiruvi, token almashinuvi, bazaga yozish) mock
so'rovlar bilan sinaldi — README'dagi eslatmaga qarang.
"""

import os
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models, auth
from ..database import get_db

router = APIRouter(prefix="/instagram", tags=["instagram"])

IG_AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
IG_TOKEN_EXCHANGE_URL = "https://api.instagram.com/oauth/access_token"
IG_LONG_LIVED_TOKEN_URL = "https://graph.instagram.com/access_token"
IG_ME_URL = "https://graph.instagram.com/me"

SCOPES = "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights,instagram_business_manage_comments"


def _get_app_config() -> tuple[str, str, str]:
    app_id = os.environ.get("IG_APP_ID")
    app_secret = os.environ.get("IG_APP_SECRET")
    redirect_uri = os.environ.get("IG_REDIRECT_URI")
    if not app_id or not app_secret or not redirect_uri:
        raise EnvironmentError("IG_APP_ID, IG_APP_SECRET, IG_REDIRECT_URI sozlanmagan")
    return app_id, app_secret, redirect_uri


@router.get("/connect")
def connect(current_user: models.User = Depends(auth.get_current_user)):
    """
    Foydalanuvchini Instagram ruxsat sahifasiga yo'naltiruvchi havolani
    qaytaradi. Frontend bu havolaga foydalanuvchini yo'naltirishi kerak
    (masalan, yangi oynada ochib).
    """
    app_id, _, redirect_uri = _get_app_config()

    # state — foydalanuvchining o'zini tasdiqlovchi JWT. Callback shu orqali
    # "kim ulayapti"ni biladi, chunki OAuth redirect'da Authorization header bo'lmaydi.
    state = auth.create_access_token({"sub": str(current_user.id)})

    authorize_url = (
        f"{IG_AUTHORIZE_URL}"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&state={state}"
    )
    return {"authorize_url": authorize_url}


@router.get("/callback")
def callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Instagram foydalanuvchini shu manzilga ?code=...&state=... bilan qaytaradi.
    Bu yerda code'ni tokenga almashtirib, akkauntni foydalanuvchiga bog'laymiz.
    """
    user_id = auth.decode_user_id(state)
    if user_id is None:
        raise HTTPException(status_code=400, detail="state parametri yaroqsiz yoki muddati o'tgan")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    app_id, app_secret, redirect_uri = _get_app_config()

    # 1-qadam: code -> qisqa muddatli token
    short_lived_resp = requests.post(
        IG_TOKEN_EXCHANGE_URL,
        data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=20,
    )
    short_lived_resp.raise_for_status()
    short_lived_data = short_lived_resp.json()
    short_lived_token = short_lived_data.get("access_token")
    ig_user_id_from_token = short_lived_data.get("user_id")

    if not short_lived_token:
        raise HTTPException(status_code=400, detail=f"Token olinmadi: {short_lived_data}")

    # 2-qadam: qisqa muddatli -> uzoq muddatli (60 kun) token
    long_lived_resp = requests.get(
        IG_LONG_LIVED_TOKEN_URL,
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_lived_token,
        },
        timeout=20,
    )
    long_lived_resp.raise_for_status()
    long_lived_data = long_lived_resp.json()
    long_lived_token = long_lived_data.get("access_token", short_lived_token)

    # 3-qadam: akkaunt ma'lumotlarini olish (username tasdiqlash uchun)
    me_resp = requests.get(
        IG_ME_URL,
        params={"fields": "id,username", "access_token": long_lived_token},
        timeout=20,
    )
    me_resp.raise_for_status()
    me_data = me_resp.json()

    ig_user_id = me_data.get("id", ig_user_id_from_token)
    username = me_data.get("username")

    # Bor bo'lsa yangilaymiz, bo'lmasa yangi yozuv yaratamiz
    account = (
        db.query(models.InstagramAccount)
        .filter(models.InstagramAccount.user_id == user.id)
        .first()
    )
    if account:
        account.ig_user_id = ig_user_id
        account.access_token = long_lived_token
        account.username = username
        account.connected_at = datetime.utcnow()
    else:
        account = models.InstagramAccount(
            user_id=user.id,
            ig_user_id=ig_user_id,
            access_token=long_lived_token,
            username=username,
        )
        db.add(account)

    db.commit()

    frontend_success_url = os.environ.get("FRONTEND_SUCCESS_URL")
    if not frontend_success_url:
        frontend_base = os.environ.get("FRONTEND_BASE_URL")
        if frontend_base:
            frontend_success_url = f"{frontend_base.rstrip('/')}/app/?instagram=connected"

    if frontend_success_url:
        return RedirectResponse(url=frontend_success_url)

    return {"status": "connected", "username": username, "ig_user_id": ig_user_id}


@router.get("/me")
def instagram_status(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Joriy foydalanuvchining ulangan Instagram akkaunti holatini qaytaradi."""
    account = (
        db.query(models.InstagramAccount)
        .filter(models.InstagramAccount.user_id == current_user.id)
        .first()
    )
    if not account:
        return {"connected": False}

    return {
        "connected": True,
        "username": account.username,
        "ig_user_id": account.ig_user_id,
        "connected_at": account.connected_at,
    }


@router.delete("/disconnect")
def disconnect(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Foydalanuvchining ulangan Instagram akkauntini o'chiradi."""
    account = (
        db.query(models.InstagramAccount)
        .filter(models.InstagramAccount.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Ulangan akkaunt topilmadi")

    db.delete(account)
    db.commit()
    return {"status": "disconnected"}
