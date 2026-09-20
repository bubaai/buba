"""
instagram_publisher.py
------------------------
Instagram professional (Business/Creator) akkauntga video (Reels) joylashni
avtomatlashtiradi. "Instagram API with Instagram Login" (Business Login for
Instagram) asosida qurilgan — bu usul Facebook Page talab qilmaydi, shuning
uchun yakka shaxs yoki kichik biznes uchun eng oson yo'l.

MUHIM CHEKLOV:
    Instagram API videoni faqat OMMAVIY (public) URL orqali oladi — ya'ni
    kompyuteringizdagi faylni to'g'ridan-to'g'ri yuklab bo'lmaydi. Video
    avval biror bulutli xotiraga (S3, Cloudflare R2, yoki hatto vaqtinchalik
    fayl hosting) joylanishi va o'sha yerdan ochiq URL olinishi kerak.

Ishlatish rejimi ikkita:
    1. CLI/yakka foydalanuvchi: IG_ACCESS_TOKEN / IG_USER_ID environment
       o'zgaruvchilari orqali (hech narsa uzatmasangiz shu ishlatiladi)
    2. Ko'p mijozli (web platforma): har bir chaqiruvda access_token va
       ig_user_id parametrlarini aniq uzatib, har bir foydalanuvchining
       o'z tokeni bilan ishlatish mumkin

Kerakli ruxsatlar (scope), OAuth paytida so'raladi:
    instagram_business_basic
    instagram_business_content_publish
    instagram_business_manage_insights   (statistika uchun)

Rasmiy hujjat: https://developers.facebook.com/docs/instagram-platform/
"""

import os
import time
import requests

GRAPH_BASE_URL = "https://graph.instagram.com"
API_VERSION = "v21.0"  # Eslatma: Meta versiyalarni muntazam yangilaydi,
                        # eng so'nggisini developers.facebook.com da tekshiring


def _get_access_token(access_token: str | None = None) -> str:
    """access_token yagona kerak bo'lgan chaqiruvlar uchun (ig_user_id shart emas)."""
    access_token = access_token or os.environ.get("IG_ACCESS_TOKEN")
    if not access_token:
        raise EnvironmentError(
            "IG access_token topilmadi. export IG_ACCESS_TOKEN='...' yoki "
            "funksiyaga access_token parametrini to'g'ridan-to'g'ri uzating."
        )
    return access_token


def _get_credentials(access_token: str | None = None, ig_user_id: str | None = None) -> tuple[str, str]:
    """
    Aniq uzatilgan qiymatlar ustuvor; berilmasa environment o'zgaruvchilarga
    qaytadi. Shu tufayli bir xil funksiyalar ham CLI'da (env var), ham
    ko'p mijozli web platformada (har user'ning o'z tokeni) ishlaydi.
    """
    access_token = access_token or os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    if not access_token or not ig_user_id:
        raise EnvironmentError(
            "IG access_token/ig_user_id topilmadi. CLI uchun:\n"
            "  export IG_ACCESS_TOKEN='...'\n"
            "  export IG_USER_ID='...'\n"
            "Yoki funksiyaga access_token/ig_user_id parametrlarini to'g'ridan-to'g'ri uzating."
        )
    return access_token, ig_user_id


def create_media_container(
    video_url: str,
    caption: str,
    media_type: str = "REELS",
    cover_url: str | None = None,
    share_to_feed: bool = True,
    access_token: str | None = None,
    ig_user_id: str | None = None,
) -> str:
    """
    1-qadam: Media konteyner yaratadi. Instagram video faylni video_url dan
    o'zi yuklab oladi (URL ommaviy bo'lishi shart).

    Qaytaradi: container_id (creation_id) — buni keyingi qadamda ishlatamiz.
    """
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)

    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{ig_user_id}/media"
    payload = {
        "video_url": video_url,
        "caption": caption,
        "media_type": media_type,
        "share_to_feed": str(share_to_feed).lower(),
        "access_token": access_token,
    }
    if cover_url:
        payload["cover_url"] = cover_url

    response = requests.post(url, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "id" not in data:
        raise RuntimeError(f"Konteyner yaratilmadi: {data}")

    return data["id"]


def wait_for_container_ready(
    container_id: str,
    timeout: int = 300,
    poll_interval: int = 5,
    access_token: str | None = None,
) -> None:
    """
    2-qadam: Instagram video faylni qayta ishlab bo'lguncha kutadi.
    status_code: IN_PROGRESS -> FINISHED (tayyor) yoki ERROR/EXPIRED (xato).
    """
    access_token = _get_access_token(access_token)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{container_id}"
    elapsed = 0

    while elapsed < timeout:
        response = requests.get(
            url, params={"fields": "status_code", "access_token": access_token}, timeout=15
        )
        response.raise_for_status()
        status = response.json().get("status_code")

        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Video qayta ishlashda xato: status={status}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"Video {timeout} soniyada tayyor bo'lmadi (status kutish tugadi)")


def publish_container(
    container_id: str, access_token: str | None = None, ig_user_id: str | None = None
) -> str:
    """3-qadam: Tayyor konteynerni Instagram'da e'lon qiladi. media_id qaytaradi."""
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)

    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{ig_user_id}/media_publish"
    payload = {"creation_id": container_id, "access_token": access_token}

    response = requests.post(url, data=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "id" not in data:
        raise RuntimeError(f"Joylash muvaffaqiyatsiz: {data}")

    return data["id"]


def post_reel(
    video_url: str,
    caption: str,
    cover_url: str | None = None,
    share_to_feed: bool = True,
    access_token: str | None = None,
    ig_user_id: str | None = None,
) -> str:
    """
    Uch qadamni birlashtirgan qulay funksiya: konteyner yaratish -> kutish -> joylash.
    Qaytaradi: nashr etilgan media_id.

    access_token/ig_user_id berilmasa, IG_ACCESS_TOKEN/IG_USER_ID env vardan olinadi
    (CLI holati). Web platformada har foydalanuvchining o'z tokeni uzatiladi.
    """
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)

    print("  [IG 1/3] Media konteyner yaratilmoqda...")
    container_id = create_media_container(
        video_url, caption, media_type="REELS", cover_url=cover_url,
        share_to_feed=share_to_feed, access_token=access_token, ig_user_id=ig_user_id,
    )

    print(f"  [IG 2/3] Video qayta ishlanishi kutilmoqda (container_id={container_id})...")
    wait_for_container_ready(container_id, access_token=access_token)

    print("  [IG 3/3] Post joylanmoqda...")
    media_id = publish_container(container_id, access_token=access_token, ig_user_id=ig_user_id)

    print(f"  Joylandi! media_id={media_id}")
    return media_id


def check_publishing_limit(access_token: str | None = None, ig_user_id: str | None = None) -> dict:
    """
    Kunlik joylash chegarasini tekshiradi (24 soatda 100 ta post limiti bor).
    Rejalashtirilgan avtomatik joylash uchun har safar oldindan tekshirish tavsiya etiladi.
    """
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{ig_user_id}/content_publishing_limit"

    response = requests.get(url, params={"access_token": access_token}, timeout=15)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Ishlatish: python instagram_publisher.py <video_url> <caption>")
        print("Eslatma: video_url ommaviy (internetdan ochiq) manzil bo'lishi shart.")
        sys.exit(1)

    post_reel(video_url=sys.argv[1], caption=sys.argv[2])
