"""
performance_analyzer.py
-------------------------
instagram_insights.py orqali olingan statistikani Claude yordamida
tahlil qilib, tushunarli hisobot va tavsiyalar chiqaradi
(masalan: "qaysi post turi yaxshi ishladi", "qachon joylash samarali").
"""

import os
import json
import anthropic

from instagram_insights import build_performance_report


def analyze_performance(report: list[dict], language: str = "uz") -> str:
    """
    Postlar statistikasi ro'yxatini Claude'ga yuborib, o'qish oson bo'lgan
    matnli hisobot va amaliy tavsiyalar oladi.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY sozlanmagan.")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""Sen Instagram content strategist va data analitiksan.
Foydalanuvchi so'nggi postlarining statistikasini beradi (JSON formatda).

Til: {language}

Vazifang:
1. Qaysi postlar yaxshi ishlagani va sababini qisqa tahlil qil
2. Umumiy naqshlarni top (masalan: qaysi kontent turi ko'proq reach oladi)
3. Keyingi postlar uchun 3-4 ta aniq, amaliy tavsiya ber

Javobni oddiy, tushunarli matn ko'rinishida yoz (JSON emas). Sarlavhalar va
ro'yxatlardan foydalanishing mumkin, lekin qisqa va aniq bo'lsin."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Postlar statistikasi:\n\n{json.dumps(report, ensure_ascii=False, indent=2)}",
            }
        ],
    )

    return response.content[0].text.strip()


def generate_weekly_report(limit: int = 10, language: str = "uz") -> str:
    """To'liq oqim: statistikani olish -> AI tahlil -> tayyor hisobot matni."""
    report = build_performance_report(limit=limit)
    if not report:
        return "Tahlil uchun postlar topilmadi."
    return analyze_performance(report, language=language)


if __name__ == "__main__":
    import sys

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(generate_weekly_report(limit=limit))
