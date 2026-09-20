"""
instagram_comments.py
------------------------
Instagram postlaridagi kommentlarni o'qish va (qo'lda tanlangan holda)
javob yozish uchun quyi darajadagi API wrapper.

MUHIM: Bu modul avtomatik javob YUBORMAYDI. reply_to_comment() faqat
siz (yoki dashboard orqali foydalanuvchi) aniq bir javobni tanlab,
o'zi chaqirganda ishlaydi.

Ishlatish rejimi ikkita (instagram_publisher.py bilan bir xil naqsh):
    1. CLI: IG_ACCESS_TOKEN environment o'zgaruvchisi
    2. Ko'p mijozli: access_token parametrini aniq uzatish

Qo'shimcha ruxsat: instagram_business_manage_comments
"""

import os
import requests

GRAPH_BASE_URL = "https://graph.instagram.com"
API_VERSION = "v21.0"


def _get_access_token(access_token: str | None = None) -> str:
    access_token = access_token or os.environ.get("IG_ACCESS_TOKEN")
    if not access_token:
        raise EnvironmentError(
            "IG access_token topilmadi. export IG_ACCESS_TOKEN='...' yoki "
            "funksiyaga access_token parametrini to'g'ridan-to'g'ri uzating."
        )
    return access_token


def get_comments(media_id: str, limit: int = 50, access_token: str | None = None) -> list[dict]:
    """
    Bitta post ostidagi kommentlarni oladi.
    Qaytaradi: [{id, text, username, timestamp, like_count}, ...]
    """
    access_token = _get_access_token(access_token)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{media_id}/comments"

    params = {
        "fields": "id,text,username,timestamp,like_count",
        "limit": limit,
        "access_token": access_token,
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json().get("data", [])


def reply_to_comment(comment_id: str, message: str, access_token: str | None = None) -> str:
    """
    Bitta kommentga javob yozadi. Bu funksiya FAQAT qo'lda, aniq bir
    komment_id va tasdiqlangan matn bilan chaqirilishi kerak — hech qachon
    avtomatik ravishda barcha kommentlarga aylantirilmasin.

    Qaytaradi: yaratilgan javob kommentining ID'si.
    """
    access_token = _get_access_token(access_token)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{comment_id}/replies"

    response = requests.post(
        url, data={"message": message, "access_token": access_token}, timeout=20
    )
    response.raise_for_status()
    data = response.json()

    if "id" not in data:
        raise RuntimeError(f"Javob yuborilmadi: {data}")

    return data["id"]


def hide_comment(comment_id: str, hide: bool = True, access_token: str | None = None) -> None:
    """Kommentni yashiradi (spam yoki nomaqbul kommentlar uchun, ixtiyoriy)."""
    access_token = _get_access_token(access_token)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{comment_id}"

    response = requests.post(
        url, data={"hide": str(hide).lower(), "access_token": access_token}, timeout=20
    )
    response.raise_for_status()


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Ishlatish: python instagram_comments.py <media_id>")
        sys.exit(1)

    comments = get_comments(sys.argv[1])
    print(json.dumps(comments, ensure_ascii=False, indent=2))
