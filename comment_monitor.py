"""
comment_monitor.py
---------------------
Oxirgi postlardagi barcha kommentlarni yig'adi, Claude yordamida
turkumlaydi (savol / shikoyat / maqtov / spam) va har biriga taklif
qilingan javob variantini tayyorlaydi.

MUHIM: Bu modul hech qanday javobni AVTOMATIK yubormaydi. Faqat
dashboard (ro'yxat) tayyorlaydi — javobni yuborish yoki yubormaslikni
foydalanuvchining o'zi hal qiladi (send_reply() ni qo'lda chaqirib).

Ishlatish:
    python3 comment_monitor.py                  # konsolda ko'rsatadi
    python3 comment_monitor.py --export          # output/ ga JSON+matn saqlaydi
    python3 comment_monitor.py --media-limit 5   # oxirgi 5 ta post tekshiriladi
"""

import os
import json
import argparse
from datetime import datetime

import anthropic

from instagram_insights import list_recent_media
from instagram_comments import get_comments, reply_to_comment

# Ustuvorlik tartibi: raqam qancha kichik bo'lsa, shuncha muhim
PRIORITY_ORDER = {"shikoyat": 1, "savol": 2, "maqtov": 3, "oddiy": 4, "spam": 5}


def _classify_batch(comments: list[dict], language: str = "uz") -> dict:
    """
    Bir nechta kommentni bitta so'rovda Claude'ga yuborib, har biri uchun
    {category, suggested_reply} oladi. Kalit — comment_id.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY sozlanmagan.")

    client = anthropic.Anthropic(api_key=api_key)

    simplified = [
        {"comment_id": c["id"], "username": c.get("username", ""), "text": c.get("text", "")}
        for c in comments
    ]

    system_prompt = f"""Sen Instagram uchun komment moderatori yordamchisisan.
Har bir kommentni quyidagi toifalardan biriga ajrat:
- "shikoyat" — norozilik, muammo, salbiy fikr
- "savol" — mahsulot/xizmat haqida savol
- "maqtov" — ijobiy fikr, tahsin
- "oddiy" — neytral, mazmunga aloqasi kam
- "spam" — reklama, aloqasiz havola, mazmunsiz

Har biri uchun {language} tilida QISQA (1-2 jumla), samimiy va tabiiy
javob taklifi yoz. Spam uchun suggested_reply ni bo'sh qoldir ("").

Faqat quyidagi JSON formatida javob ber, boshqa hech narsa yozma:

{{
  "<comment_id>": {{"category": "...", "suggested_reply": "..."}},
  ...
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(simplified, ensure_ascii=False)}],
    )

    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    return json.loads(raw_text)


def build_dashboard(
    media_limit: int = 10,
    comments_per_media: int = 50,
    language: str = "uz",
    access_token: str | None = None,
    ig_user_id: str | None = None,
) -> list[dict]:
    """
    Oxirgi postlar bo'yicha barcha kommentlarni yig'ib, turkumlab,
    ustuvorlik bo'yicha saralangan ro'yxat qaytaradi.
    """
    media_list = list_recent_media(limit=media_limit, access_token=access_token, ig_user_id=ig_user_id)
    all_items = []

    for media in media_list:
        try:
            comments = get_comments(media["id"], limit=comments_per_media, access_token=access_token)
        except Exception as e:
            print(f"  Ogohlantirish: {media['id']} uchun kommentlar olinmadi ({e})")
            continue

        if not comments:
            continue

        classifications = _classify_batch(comments, language=language)

        for c in comments:
            info = classifications.get(c["id"], {"category": "oddiy", "suggested_reply": ""})
            all_items.append(
                {
                    "comment_id": c["id"],
                    "username": c.get("username", ""),
                    "text": c.get("text", ""),
                    "timestamp": c.get("timestamp"),
                    "media_id": media["id"],
                    "media_permalink": media.get("permalink"),
                    "category": info.get("category", "oddiy"),
                    "suggested_reply": info.get("suggested_reply", ""),
                }
            )

    all_items.sort(key=lambda x: PRIORITY_ORDER.get(x["category"], 9))
    return all_items


def print_dashboard(items: list[dict]) -> None:
    if not items:
        print("Kommentlar topilmadi.")
        return

    labels = {
        "shikoyat": "🔴 SHIKOYAT",
        "savol": "🟡 SAVOL",
        "maqtov": "🟢 MAQTOV",
        "oddiy": "⚪ ODDIY",
        "spam": "🚫 SPAM",
    }

    for item in items:
        label = labels.get(item["category"], item["category"].upper())
        print(f"\n[{label}] @{item['username']}")
        print(f"  Komment: {item['text']}")
        if item["suggested_reply"]:
            print(f"  Taklif javob: {item['suggested_reply']}")
        print(f"  comment_id: {item['comment_id']}")

    counts = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    print("\n--- Xulosa ---")
    for cat, count in sorted(counts.items(), key=lambda x: PRIORITY_ORDER.get(x[0], 9)):
        print(f"  {labels.get(cat, cat)}: {count}")


def export_dashboard(items: list[dict], output_dir: str = "output") -> tuple[str, str]:
    """Dashboard'ni JSON va o'qilishi oson matn fayl sifatida saqlaydi."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    json_path = os.path.join(output_dir, f"comments_dashboard_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    txt_path = os.path.join(output_dir, f"comments_dashboard_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(f"[{item['category'].upper()}] @{item['username']}\n")
            f.write(f"Komment: {item['text']}\n")
            if item["suggested_reply"]:
                f.write(f"Taklif javob: {item['suggested_reply']}\n")
            f.write(f"comment_id: {item['comment_id']}\n")
            f.write(f"post: {item.get('media_permalink', '')}\n\n")

    return json_path, txt_path


def send_reply(comment_id: str, message: str, access_token: str | None = None) -> str:
    """
    Bitta kommentga javobni QO'LDA yuborish uchun qulay wrapper.
    Faqat foydalanuvchi dashboard'dan biror javobni ko'rib, tasdiqlab,
    aynan shu funksiyani o'zi chaqirganda ishlatiladi.
    """
    return reply_to_comment(comment_id, message, access_token=access_token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram komment monitoring dashboard")
    parser.add_argument("--media-limit", type=int, default=10, help="Nechta oxirgi post tekshirilsin")
    parser.add_argument("--comments-per-media", type=int, default=50, help="Har post uchun max komment soni")
    parser.add_argument("--language", default="uz", help="Taklif javoblar tili")
    parser.add_argument("--export", action="store_true", help="Natijani output/ papkasiga saqlash")

    args = parser.parse_args()

    dashboard = build_dashboard(
        media_limit=args.media_limit,
        comments_per_media=args.comments_per_media,
        language=args.language,
    )
    print_dashboard(dashboard)

    if args.export:
        json_path, txt_path = export_dashboard(dashboard)
        print(f"\nSaqlandi: {json_path}")
        print(f"Saqlandi: {txt_path}")
