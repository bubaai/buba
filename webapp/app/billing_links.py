"""
billing_links.py
-------------------
Payme va Click uchun to'lov sahifasiga yo'naltiruvchi havolalarni yaratadi.
Foydalanuvchi shu havola orqali Payme/Click checkout sahifasiga o'tadi,
u yerda to'lovni tasdiqlaydi, so'ng Payme/Click bizning webhook'ga
xabar yuboradi (payme_router.py / click_router.py).

Talab qilinadigan environment o'zgaruvchilar:
    PAYME_MERCHANT_ID
    CLICK_SERVICE_ID, CLICK_MERCHANT_ID
"""

import os
import base64


def generate_payme_link(subscription_id: int, amount_uzs: float, return_url: str | None = None) -> str:
    """
    Payme checkout havolasini yaratadi.
    Havola formati: https://checkout.paycom.uz/<base64(parametrlar)>
    Summani Payme "tiyin"da kutadi (1 so'm = 100 tiyin).
    """
    merchant_id = os.environ.get("PAYME_MERCHANT_ID")
    if not merchant_id:
        raise EnvironmentError("PAYME_MERCHANT_ID sozlanmagan")

    amount_tiyin = int(round(amount_uzs * 100))
    params = f"m={merchant_id};ac.subscription_id={subscription_id};a={amount_tiyin}"
    if return_url:
        params += f";c={return_url}"

    encoded = base64.b64encode(params.encode()).decode()
    return f"https://checkout.paycom.uz/{encoded}"


def generate_click_link(subscription_id: int, amount_uzs: float, return_url: str | None = None) -> str:
    """Click checkout havolasini yaratadi (Shop API orqali to'lov)."""
    service_id = os.environ.get("CLICK_SERVICE_ID")
    merchant_id = os.environ.get("CLICK_MERCHANT_ID")
    if not service_id or not merchant_id:
        raise EnvironmentError("CLICK_SERVICE_ID va CLICK_MERCHANT_ID sozlanmagan")

    url = (
        "https://my.click.uz/services/pay"
        f"?service_id={service_id}"
        f"&merchant_id={merchant_id}"
        f"&amount={amount_uzs}"
        f"&transaction_param={subscription_id}"
    )
    if return_url:
        url += f"&return_url={return_url}"

    return url
