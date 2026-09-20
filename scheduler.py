"""
scheduler.py
-------------
Postlarni oldindan rejalashtirish uchun oddiy navbat (queue) tizimi.
JSON faylda saqlanadi — alohida baza kerak emas, bitta foydalanuvchi
uchun yetarli.

Ishlash tartibi:
    1. add_scheduled_post() orqali post navbatga qo'shiladi (video yo'li,
       caption, qachon joylanishi kerakligi)
    2. run_due_posts() vaqti kelgan postlarni topib, R2'ga yuklab,
       Instagram'ga joylaydi
    3. Bu funksiyani muntazam chaqirish uchun tizim cron'iga yoziladi
       (masalan, har 5 daqiqada)

Cron misoli (har 5 daqiqada tekshiradi):
    */5 * * * * cd /path/to/ai-content-agent && python3 scheduler.py run >> scheduler.log 2>&1
"""

import os
import json
import argparse
from datetime import datetime

from cloud_storage import upload_video
from instagram_publisher import post_reel

QUEUE_FILE = "scheduler_queue.json"


def _load_queue(queue_file: str = QUEUE_FILE) -> list[dict]:
    if not os.path.exists(queue_file):
        return []
    with open(queue_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_queue(queue: list[dict], queue_file: str = QUEUE_FILE) -> None:
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def add_scheduled_post(
    video_path: str,
    caption: str,
    scheduled_time: str,
    queue_file: str = QUEUE_FILE,
) -> dict:
    """
    Navbatga yangi post qo'shadi.

    scheduled_time: ISO format, masalan "2026-09-25T18:00:00"
                     (mahalliy vaqt zonangizda)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video topilmadi: {video_path}")

    # Format tekshiruvi — xato formatda vaqt kiritilsa, darhol bildiradi
    datetime.fromisoformat(scheduled_time)

    queue = _load_queue(queue_file)
    entry = {
        "id": f"post_{len(queue) + 1}_{int(datetime.now().timestamp())}",
        "video_path": video_path,
        "caption": caption,
        "scheduled_time": scheduled_time,
        "status": "pending",  # pending -> published / failed
        "created_at": datetime.now().isoformat(),
        "published_at": None,
        "media_id": None,
        "error": None,
    }
    queue.append(entry)
    _save_queue(queue, queue_file)
    return entry


def list_scheduled(queue_file: str = QUEUE_FILE, status: str | None = None) -> list[dict]:
    """Navbatdagi postlarni ko'rsatadi, xohlasa status bo'yicha filtrlab."""
    queue = _load_queue(queue_file)
    if status:
        queue = [item for item in queue if item["status"] == status]
    return queue


def cancel_scheduled_post(post_id: str, queue_file: str = QUEUE_FILE) -> bool:
    """Hali joylanmagan postni navbatdan olib tashlaydi."""
    queue = _load_queue(queue_file)
    for item in queue:
        if item["id"] == post_id and item["status"] == "pending":
            item["status"] = "cancelled"
            _save_queue(queue, queue_file)
            return True
    return False


def run_due_posts(queue_file: str = QUEUE_FILE) -> list[dict]:
    """
    Vaqti kelgan ("pending" va scheduled_time <= hozir) postlarni topib,
    ketma-ket joylaydi. Har birining natijasini qaytaradi.
    """
    queue = _load_queue(queue_file)
    now = datetime.now()
    results = []

    for item in queue:
        if item["status"] != "pending":
            continue

        scheduled_dt = datetime.fromisoformat(item["scheduled_time"])
        if scheduled_dt > now:
            continue

        print(f"Joylanmoqda: {item['id']} ({item['video_path']})")
        try:
            remote_key = f"scheduled/{os.path.basename(item['video_path'])}"
            public_url = upload_video(item["video_path"], remote_key=remote_key)
            media_id = post_reel(video_url=public_url, caption=item["caption"])

            item["status"] = "published"
            item["published_at"] = datetime.now().isoformat()
            item["media_id"] = media_id
            print(f"  Muvaffaqiyatli: media_id={media_id}")

        except Exception as e:
            item["status"] = "failed"
            item["error"] = str(e)
            print(f"  XATO: {e}")

        results.append(item)

    _save_queue(queue, queue_file)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post rejalashtirish tizimi")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Navbatga post qo'shish")
    add_parser.add_argument("video_path")
    add_parser.add_argument("caption")
    add_parser.add_argument("scheduled_time", help="ISO format: 2026-09-25T18:00:00")

    subparsers.add_parser("list", help="Navbatni ko'rsatish")
    subparsers.add_parser("run", help="Vaqti kelgan postlarni joylash")

    cancel_parser = subparsers.add_parser("cancel", help="Postni bekor qilish")
    cancel_parser.add_argument("post_id")

    args = parser.parse_args()

    if args.command == "add":
        entry = add_scheduled_post(args.video_path, args.caption, args.scheduled_time)
        print(f"Qo'shildi: {entry['id']} — {entry['scheduled_time']}")

    elif args.command == "list":
        items = list_scheduled()
        if not items:
            print("Navbat bo'sh.")
        for item in items:
            print(f"[{item['status'].upper()}] {item['id']} — {item['scheduled_time']} — {item['video_path']}")

    elif args.command == "run":
        results = run_due_posts()
        print(f"\n{len(results)} ta post qayta ishlandi.")

    elif args.command == "cancel":
        success = cancel_scheduled_post(args.post_id)
        print("Bekor qilindi." if success else "Post topilmadi yoki allaqachon joylangan.")
