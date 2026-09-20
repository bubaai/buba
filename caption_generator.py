"""
caption_generator.py
---------------------
Video transkripsiyasi (yoki qisqacha mavzu tavsifi) asosida
Instagram uchun caption (post matni) va hashtaglar generatsiya qiladi.

Talab: ANTHROPIC_API_KEY environment variable o'rnatilgan bo'lishi kerak.
    export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import json
import anthropic


def generate_caption(
    transcript: str,
    niche: str = "shaxsiy brend",
    tone: str = "samimiy va professional",
    language: str = "uz",
) -> dict:
    """
    Transkripsiya asosida Instagram caption + hashtaglar yaratadi.

    Qaytaradi: {"caption": str, "hashtags": list[str], "cta": str}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY topilmadi. Terminalda: export ANTHROPIC_API_KEY='sizning-kalitingiz'"
        )

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""Sen Instagram uchun content strategist san'atkorisan.
Foydalanuvchi videosining transkripsiyasi asosida jozibali post yozasan.

Til: {language}
Soha: {niche}
Ohang: {tone}

Faqat quyidagi JSON formatida javob ber, hech qanday qo'shimcha matn, izoh yoki
markdown belgilarisiz (```json kabi belgilar ham bo'lmasin):

{{
  "caption": "Post matni (3-5 jumla, diqqatni tortadigan birinchi qator bilan)",
  "hashtags": ["#misol1", "#misol2", "... 10-15 ta hashtag"],
  "cta": "Qisqa call-to-action (masalan: 'Fikringizni komentda yozing')"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Video transkripsiyasi:\n\n{transcript}",
            }
        ],
    )

    raw_text = message.content[0].text.strip()

    # Ehtiyot chorasi: model ba'zan ```json qatorlari bilan qaytarishi mumkin
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model javobi JSON formatda emas: {raw_text[:300]}") from e

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Ishlatish: python caption_generator.py '<transkripsiya matni>' [soha] [til]")
        sys.exit(1)

    transcript_arg = sys.argv[1]
    niche_arg = sys.argv[2] if len(sys.argv) > 2 else "shaxsiy brend"
    lang_arg = sys.argv[3] if len(sys.argv) > 3 else "uz"

    result = generate_caption(transcript_arg, niche=niche_arg, language=lang_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
