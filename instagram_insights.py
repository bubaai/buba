"""
instagram_insights.py
-----------------------
Instagram professional akkaunt va postlar statistikasini oladi:
ko'rishlar, layklar, saqlashlar, ulashishlar, follower o'sishi va h.k.

Ishlatish rejimi ikkita (instagram_publisher.py bilan bir xil naqsh):
    1. CLI: IG_ACCESS_TOKEN / IG_USER_ID environment o'zgaruvchilari
    2. Ko'p mijozli: access_token / ig_user_id parametrlarini aniq uzatish

Qo'shimcha ruxsat kerak: instagram_business_manage_insights
"""

import os
import requests

GRAPH_BASE_URL = "https://graph.instagram.com"
API_VERSION = "v21.0"


def _get_credentials(access_token: str | None = None, ig_user_id: str | None = None) -> tuple[str, str]:
    access_token = access_token or os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    if not access_token or not ig_user_id:
        raise EnvironmentError(
            "IG access_token/ig_user_id topilmadi. CLI uchun IG_ACCESS_TOKEN/IG_USER_ID "
            "env var, yoki funksiyaga parametr sifatida uzating."
        )
    return access_token, ig_user_id


def list_recent_media(limit: int = 25, access_token: str | None = None, ig_user_id: str | None = None) -> list[dict]:
    """Oxirgi postlar ro'yxatini oladi (id, caption, sana, permalink, turi)."""
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{ig_user_id}/media"

    params = {
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink",
        "limit": limit,
        "access_token": access_token,
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json().get("data", [])


def get_media_insights(
    media_id: str, media_product_type: str = "REELS", access_token: str | None = None
) -> dict:
    """
    Bitta post uchun statistika oladi.

    Reels uchun metriclar feed post'dan farq qiladi — shuning uchun
    media_product_type parametri muhim.
    """
    if not access_token:
        access_token = os.environ.get("IG_ACCESS_TOKEN")
    if not access_token:
        raise EnvironmentError("IG access_token topilmadi.")

    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{media_id}/insights"

    if media_product_type == "REELS":
        metrics = "reach,likes,comments,saved,shares,total_interactions,plays"
    else:
        metrics = "reach,likes,comments,saved,shares,total_interactions"

    response = requests.get(
        url, params={"metric": metrics, "access_token": access_token}, timeout=20
    )
    response.raise_for_status()
    data = response.json().get("data", [])

    # Natijani {metric_name: value} shaklidagi qulay dict'ga o'giramiz
    result = {}
    for item in data:
        name = item.get("name")
        values = item.get("values", [{}])
        result[name] = values[0].get("value") if values else None

    return result


def get_account_insights(
    period: str = "day", days: int = 7, access_token: str | None = None, ig_user_id: str | None = None
) -> dict:
    """
    Akkaunt darajasidagi statistika: reach, impressions, follower_count o'zgarishi.
    period: day / week / days_28
    """
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)
    url = f"{GRAPH_BASE_URL}/{API_VERSION}/{ig_user_id}/insights"

    metrics = "reach,follower_count,profile_views"
    params = {
        "metric": metrics,
        "period": period,
        "access_token": access_token,
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def build_performance_report(
    limit: int = 10, access_token: str | None = None, ig_user_id: str | None = None
) -> list[dict]:
    """
    Oxirgi postlar + ularning statistikasini birlashtirib, oddiy hisobot
    tuzadi. Bu ma'lumotni keyin AI (Claude) orqali tahlil qilish mumkin.
    """
    access_token, ig_user_id = _get_credentials(access_token, ig_user_id)
    media_list = list_recent_media(limit=limit, access_token=access_token, ig_user_id=ig_user_id)
    report = []

    for media in media_list:
        try:
            insights = get_media_insights(
                media["id"],
                media_product_type=media.get("media_product_type", "FEED"),
                access_token=access_token,
            )
        except requests.HTTPError:
            insights = {}

        report.append(
            {
                "id": media["id"],
                "caption": (media.get("caption") or "")[:80],
                "timestamp": media.get("timestamp"),
                "permalink": media.get("permalink"),
                "insights": insights,
            }
        )

    return report


if __name__ == "__main__":
    import json

    report = build_performance_report(limit=5)
    print(json.dumps(report, ensure_ascii=False, indent=2))
