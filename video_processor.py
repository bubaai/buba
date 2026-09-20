"""
video_processor.py
-------------------
Xom videoni Instagram Reels formatiga (9:16, vertikal) moslashtiradi.

Nima qiladi:
- Videoni 1080x1920 (9:16) formatga scale+crop qiladi (cho'zilib ketmasligi uchun)
- Agar video gorizontal bo'lsa, avtomatik markazdan kesib vertikal qiladi
- Uzunligini (max_duration) belgilangan chegaraga qisqartiradi (Reels uchun odatda 90s)
- Ovoz sifatini saqlab, faylni H.264/AAC formatida eksport qiladi

Talab: tizimda ffmpeg o'rnatilgan bo'lishi kerak.
"""

import subprocess
import json
import os


def get_video_info(input_path: str) -> dict:
    """ffprobe orqali video haqida asosiy ma'lumot (o'lcham, davomiylik) oladi."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    duration = float(data["format"].get("duration", 0))
    width = int(video_stream["width"])
    height = int(video_stream["height"])

    return {"width": width, "height": height, "duration": duration}


def convert_to_reels_format(
    input_path: str,
    output_path: str,
    max_duration: float = 90.0,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """
    Videoni 9:16 Reels formatiga o'giradi.

    - Agar video allaqachon vertikal bo'lsa: shunchaki target o'lchamga scale qiladi
    - Agar gorizontal yoki kvadrat bo'lsa: markazdan crop qilib vertikal qiladi
    - max_duration dan uzun bo'lsa, boshidan kesadi
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Kirish fayli topilmadi: {input_path}")

    info = get_video_info(input_path)
    duration = min(info["duration"], max_duration)

    # scale qilib, keyin markazdan crop qilish — aspekt nisbatini buzmasdan
    # to'ldirish uchun standart usul: scale to cover, then crop to exact size
    vf_filter = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-vf", vf_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Ishlatish: python video_processor.py <kirish.mp4> <chiqish.mp4>")
        sys.exit(1)

    convert_to_reels_format(sys.argv[1], sys.argv[2])
    print(f"Tayyor: {sys.argv[2]}")
