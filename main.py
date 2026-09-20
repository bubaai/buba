"""
main.py
-------
Butun pipeline'ni birlashtiradi:

  xom video -> Reels formatga o'girish -> subtitr yaratish ->
  subtitrni videoga kuydirish -> AI caption/hashtag generatsiya ->
  (ixtiyoriy) R2'ga yuklash -> Instagram'ga avtomatik joylash

Natija: /output papkasida tayyor video + caption.txt fayli.
--publish bayrog'i bilan to'g'ridan-to'g'ri Instagram'ga ham joylanadi.

Ishlatish:
    export ANTHROPIC_API_KEY="sizning-kalitingiz"
    python3 main.py input/video.mp4 --niche "fitnes" --language uz

    # Instagram'ga avtomatik joylash bilan:
    export IG_ACCESS_TOKEN="..." IG_USER_ID="..."
    export R2_ACCOUNT_ID="..." R2_ACCESS_KEY_ID="..." R2_SECRET_ACCESS_KEY="..." \\
           R2_BUCKET_NAME="..." R2_PUBLIC_BASE_URL="..."
    python3 main.py input/video.mp4 --publish
"""

import argparse
import os
import json

from video_processor import convert_to_reels_format
from subtitle_generator import transcribe_to_srt, burn_subtitles
from caption_generator import generate_caption
from cloud_storage import upload_video
from instagram_publisher import post_reel


def run_pipeline(
    input_video: str,
    output_dir: str = "output",
    niche: str = "shaxsiy brend",
    language: str = "uz",
    whisper_model: str = "base",
    max_duration: float = 90.0,
    burn_subs: bool = True,
    publish: bool = False,
    ig_access_token: str | None = None,
    ig_user_id: str | None = None,
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_video))[0]

    reels_path = os.path.join(output_dir, f"{base_name}_reels.mp4")
    srt_path = os.path.join(output_dir, f"{base_name}.srt")
    final_video_path = os.path.join(output_dir, f"{base_name}_final.mp4")
    caption_path = os.path.join(output_dir, f"{base_name}_caption.txt")

    print("1) Reels formatga o'girilmoqda (9:16)...")
    convert_to_reels_format(input_video, reels_path, max_duration=max_duration)

    print("2) Ovoz matnga o'girilmoqda (transkripsiya)...")
    transcript = transcribe_to_srt(reels_path, srt_path, model_size=whisper_model)
    print(f"      Transkripsiya: {transcript[:150]}...")

    working_video = reels_path
    if burn_subs and transcript.strip():
        print("3) Subtitr videoga qo'shilmoqda...")
        burn_subtitles(reels_path, srt_path, final_video_path)
        working_video = final_video_path
    else:
        print("3) Subtitr o'tkazib yuborildi (ovoz topilmadi yoki o'chirilgan)")
        working_video = reels_path

    print("4) AI caption va hashtag generatsiya qilinmoqda...")
    caption_data = generate_caption(transcript, niche=niche, language=language)

    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption_data["caption"] + "\n\n")
        f.write(" ".join(caption_data["hashtags"]) + "\n\n")
        f.write(caption_data["cta"] + "\n")

    result = {
        "video_path": working_video,
        "srt_path": srt_path,
        "caption_path": caption_path,
        "caption_data": caption_data,
        "transcript": transcript,
    }

    if publish:
        print("5) Videoga ochiq URL berilmoqda va Instagram'ga joylanmoqda...")
        remote_key = f"reels/{os.path.basename(working_video)}"
        public_url = upload_video(working_video, remote_key=remote_key)
        print(f"      Ochiq URL: {public_url}")

        full_caption = (
            caption_data["caption"]
            + "\n\n"
            + " ".join(caption_data["hashtags"])
            + "\n\n"
            + caption_data["cta"]
        )
        media_id = post_reel(
            video_url=public_url, caption=full_caption,
            access_token=ig_access_token, ig_user_id=ig_user_id,
        )
        result["instagram_media_id"] = media_id
        result["public_video_url"] = public_url

    print("\n=== TAYYOR ===")
    print(f"Video: {working_video}")
    print(f"Caption: {caption_path}")
    if publish:
        print(f"Instagram media_id: {result.get('instagram_media_id')}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI kontent agenti - video ishlov pipeline")
    parser.add_argument("input_video", help="Kirish video fayli yo'li")
    parser.add_argument("--output-dir", default="output", help="Chiqish papkasi")
    parser.add_argument("--niche", default="shaxsiy brend", help="Kontent sohasi (masalan: fitnes, ta'lim)")
    parser.add_argument("--language", default="uz", help="Caption tili: uz, en, ru")
    parser.add_argument("--whisper-model", default="base", help="tiny/base/small/medium/large-v3")
    parser.add_argument("--max-duration", type=float, default=90.0, help="Maksimal video uzunligi (soniya)")
    parser.add_argument("--no-subs", action="store_true", help="Subtitr kuydirishni o'chirish")
    parser.add_argument(
        "--publish", action="store_true",
        help="Videoni R2'ga yuklab, Instagram'ga avtomatik joylash (R2_* va IG_* env kerak)"
    )

    args = parser.parse_args()

    run_pipeline(
        input_video=args.input_video,
        output_dir=args.output_dir,
        niche=args.niche,
        language=args.language,
        whisper_model=args.whisper_model,
        max_duration=args.max_duration,
        burn_subs=not args.no_subs,
        publish=args.publish,
    )
