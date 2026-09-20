"""
subtitle_generator.py
----------------------
Videodagi ovozni matnga o'giradi (transkripsiya) va:
1. .srt subtitr fayl yaratadi
2. Xohlasa, subtitrni to'g'ridan-to'g'ri videoga "kuydiradi" (burn-in)

Model lokal ishlaydi (internetga ulanish shart emas, birinchi marta model
yuklab olinadi). Katta modellar aniqroq, lekin sekinroq ishlaydi.
"""

import subprocess
from faster_whisper import WhisperModel


def transcribe_to_srt(
    video_path: str,
    srt_output_path: str,
    model_size: str = "base",
    language: str | None = None,
) -> str:
    """
    Videodagi audio ustidan transkripsiya qilib, .srt faylga yozadi.

    model_size: tiny / base / small / medium / large-v3
        - tiny/base: tez, kam resurs, o'rtacha aniqlik
        - small/medium: sekinroq, yaxshiroq aniqlik
    language: "uz", "en", "ru" va h.k. — None bo'lsa avtomatik aniqlanadi
    """
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(video_path, language=language, vad_filter=True)

    def format_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    full_text_parts = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.start)
        end = format_timestamp(seg.end)
        text = seg.text.strip()
        full_text_parts.append(text)
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    with open(srt_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Keyinchalik caption generatsiyasi uchun to'liq matnni ham qaytaramiz
    full_transcript = " ".join(full_text_parts)
    return full_transcript


def burn_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """Subtitrni videoga doimiy (burn-in) qo'shadi — ffmpeg subtitles filtri orqali."""
    # ffmpeg subtitles filtri uchun yo'lni escape qilish kerak (ayniqsa Windows'da,
    # lekin Linux'da ham maxsus belgilar bo'lsa muammo bo'lishi mumkin)
    escaped_srt = srt_path.replace(":", "\\:")

    style = "FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={escaped_srt}:force_style='{style}'",
        "-c:a", "copy",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Ishlatish: python subtitle_generator.py <video.mp4> <chiqish.srt> [model_size]")
        sys.exit(1)

    model_size = sys.argv[3] if len(sys.argv) > 3 else "base"
    transcript = transcribe_to_srt(sys.argv[1], sys.argv[2], model_size=model_size)
    print(f"Subtitr tayyor: {sys.argv[2]}")
    print(f"Transkripsiya: {transcript[:200]}...")
