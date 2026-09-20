# AI Content Agent — MVP (1, 2, 3 va 4-bosqich)

Xom videoni Instagram Reels'ga tayyor holga keltiradi, avtomatik joylaydi
va statistikasini AI orqali tahlil qiladi. Komentlarga avtomatik javob
ataylab qo'shilmagan — bu qism siz so'ragan holda alohida qaraladi.

## Nima qiladi

**1-bosqich — Video tayyorlash:**
1. **Video formatlash** — istalgan o'lchamdagi videoni 1080x1920 (9:16,
   Reels formati) ga o'giradi, uzunligini kesadi
2. **Subtitr** — ovozni matnga o'giradi (lokal, internetsiz ishlaydi,
   faqat birinchi marta model yuklanadi) va videoga kuydiradi
3. **Caption + hashtag** — Claude API orqali transkripsiya asosida
   Instagram posti uchun matn, hashtaglar va call-to-action yozadi

**2-bosqich — Instagram integratsiyasi:**
4. **Avtomatik joylash** — Instagram Graph API orqali Reels'ni to'g'ridan-
   to'g'ri akkauntga joylaydi
5. **Statistika tahlili** — postlar bo'yicha reach, layk, saqlash kabi
   ko'rsatkichlarni oladi va Claude orqali tushunarli hisobot + tavsiyalar
   chiqaradi

**3-bosqich — Komment monitoring:**
6. **Komment dashboard** — barcha oxirgi postlardagi kommentlarni yig'adi,
   Claude yordamida turkumlaydi (shikoyat/savol/maqtov/spam) va har biriga
   javob taklifi tayyorlaydi. **Avtomatik javob yubormaydi** — faqat
   ro'yxat va tavsiyalarni ko'rsatadi, yuborish qarorini siz qabul qilasiz

**4-bosqich — Obuna platformasi:**
7. **Ko'p mijozli web backend + frontend** (`webapp/` papkasida) —
   foydalanuvchilar ro'yxatdan o'tadi, tarif tanlaydi, **Payme** yoki
   **Click** orqali to'laydi, obuna avtomatik faollashadi. Har bir
   foydalanuvchi o'z **Instagram akkauntini web orqali ulaydi** va video
   yuklab, fon vazifasi orqali (obuna faol bo'lsagina) kontent
   pipeline'ini ishga tushiradi. Hammasi bitta sahifali frontend orqali
   (`/app/`). 36 ta avtomatik tekshiruv o'tdi, jumladan haqiqiy brauzerda
   (Playwright) tekshirilgan interfeys. Batafsil: `webapp/README.md`

## O'rnatish

### 1. Tizim talablari
- Python 3.10+
- FFmpeg (video ishlov uchun shart)

```bash
# Ubuntu/Debian uchun ffmpeg o'rnatish:
sudo apt update && sudo apt install ffmpeg

# macOS uchun:
brew install ffmpeg
```

### 2. Python kutubxonalari

```bash
cd ai-content-agent
pip install -r requirements.txt
```

### 3. API kalitni sozlash

Claude API kalitingizni https://console.anthropic.com dan oling, so'ng:

```bash
export ANTHROPIC_API_KEY="sk-ant-sizning-kalitingiz"
```

Doimiy saqlash uchun buni `~/.bashrc` yoki `~/.zshrc` fayliga qo'shing.

## Ishlatish

Eng oddiy holat:

```bash
python3 main.py input/mening_videom.mp4
```

Sozlamalar bilan:

```bash
python3 main.py input/mening_videom.mp4 \
    --niche "fitnes" \
    --language uz \
    --whisper-model small \
    --max-duration 60
```

### Parametrlar

| Parametr | Tavsif | Standart |
|---|---|---|
| `input_video` | Kirish video fayli (majburiy) | — |
| `--output-dir` | Natijalar saqlanadigan papka | `output` |
| `--niche` | Kontent sohasi (fitnes, ta'lim, oshxona...) | `shaxsiy brend` |
| `--language` | Caption tili: `uz`, `en`, `ru` | `uz` |
| `--whisper-model` | `tiny`/`base`/`small`/`medium`/`large-v3` | `base` |
| `--max-duration` | Maksimal video uzunligi (soniya) | `90` |
| `--no-subs` | Subtitr qo'shmaslik | o'chirilgan |

**Eslatma — model tanlash:** `tiny` va `base` tez ishlaydi, lekin ba'zan
xato qiladi. `small` yoki `medium` sekinroq, ammo ancha aniqroq. Kuchli
kompyuteringiz bo'lmasa, `base`dan boshlang.

## Natija

`output/` papkasida quyidagilar paydo bo'ladi:

- `<nom>_final.mp4` — subtitrli, Reels formatidagi tayyor video
- `<nom>.srt` — subtitr fayli (agar alohida kerak bo'lsa)
- `<nom>_caption.txt` — caption, hashtaglar va CTA matni

Bu fayllarni qo'lda Instagramga joylashingiz mumkin, yoki quyida
tavsiflangan `--publish` bayrog'i orqali avtomatik joylashingiz mumkin.

## Instagram bilan ulanish (2-bosqich sozlamasi)

### 1. Akkauntni Professional qilish
Instagram akkaunt **Business** yoki **Creator** turida bo'lishi shart
(shaxsiy akkauntlar API bilan ishlamaydi). Instagram ilovasida: Sozlamalar
→ Akkaunt turi → Professional akkauntga o'tish.

### 2. Meta App yaratish
1. https://developers.facebook.com/apps → "Create App" → turini "Business" deb tanlang
2. App Dashboard'da **Instagram** mahsulotini qo'shing
3. "API setup with Instagram login" (Business Login for Instagram) bo'limini tanlang
   — bu usul Facebook Page talab qilmaydi, yakka foydalanuvchi/kichik biznes uchun eng oson

### 3. Ruxsatlar (scope)
OAuth so'rovida quyidagi ruxsatlar kerak:
- `instagram_business_basic`
- `instagram_business_content_publish`
- `instagram_business_manage_insights` (statistika uchun)
- `instagram_business_manage_comments` (komment monitoring uchun)

### 4. Access token va User ID olish
Business Login orqali foydalanuvchi ruxsat bergach, qisqa muddatli token
olasiz — uni **uzoq muddatli tokenga** (60 kun) almashtiring. Keyin:

```bash
export IG_ACCESS_TOKEN="olingan-uzoq-muddatli-token"
export IG_USER_ID="instagram-professional-akkaunt-id"
```

To'liq OAuth qadamlari: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login

### 5. Video uchun ochiq (public) URL — Cloudflare R2

Instagram API videoni faylni to'g'ridan-to'g'ri qabul qilmaydi — u
ko'rsatilgan URL'dan videoni o'zi yuklab oladi. Shuning uchun `main.py`
tayyorlagan video avval **Cloudflare R2**'ga yuklanadi (S3-mos, egress
trafigi bepul — video kabi katta fayllar uchun qulay).

**Sozlash:**
1. https://dash.cloudflare.com → R2 → "Create bucket" (masalan: `ai-agent-videos`)
2. Bucket → Settings → Public Access → yoqing — sizga `pub-xxxxx.r2.dev`
   ko'rinishidagi ochiq domen beriladi
3. R2 → "Manage R2 API Tokens" → yangi token yarating (Object Read & Write ruxsati bilan)
4. Quyidagilarni sozlang:

```bash
export R2_ACCOUNT_ID="cloudflare-account-id"
export R2_ACCESS_KEY_ID="token-access-key"
export R2_SECRET_ACCESS_KEY="token-secret-key"
export R2_BUCKET_NAME="ai-agent-videos"
export R2_PUBLIC_BASE_URL="https://pub-xxxxx.r2.dev"
```

### Hammasi birga — avtomatik joylash

Video tayyorlash + R2'ga yuklash + Instagram'ga joylashning barchasi
bitta buyruqda:

```bash
python3 main.py input/mening_videom.mp4 --niche "fitnes" --publish
```

`--publish` bo'lmasa, pipeline faqat video/caption tayyorlaydi (joylamaydi) —
shunda tayyor faylni qo'lda ko'rib, keyin alohida joylashingiz mumkin:

```bash
python3 cloud_storage.py output/mening_videom_final.mp4
python3 instagram_publisher.py "<yuqoridagi_url>" "$(cat output/mening_videom_caption.txt)"
```

### Statistika olish va AI tahlil

```bash
# Xom statistika (JSON):
python3 instagram_insights.py

# AI tomonidan yozilgan tushunarli hisobot va tavsiyalar:
python3 performance_analyzer.py
```

## Komment monitoring (3-bosqich)

Qo'shimcha ruxsat kerak: `instagram_business_manage_comments`

```bash
# Dashboard'ni konsolda ko'rish (oxirgi 10 ta post kommentlari):
python3 comment_monitor.py

# Natijani output/ papkasiga saqlash (JSON + o'qilishi oson matn):
python3 comment_monitor.py --export

# Faqat oxirgi 3 ta postni tekshirish:
python3 comment_monitor.py --media-limit 3
```

Dashboard har bir kommentni **shikoyat → savol → maqtov → oddiy → spam**
tartibida ko'rsatadi va har biriga tayyor javob taklifini beradi. Biror
javobni yuborish uchun uni ko'rib chiqib, `comment_id`sini quyidagicha
ishlating:

```python
from comment_monitor import send_reply
send_reply("17873440459141029", "Rahmat, savolingiz uchun! DM orqali batafsil yozamiz.")
```

**Bu ataylab yarim avtomatik:** tizim javobni taklif qiladi, lekin uni
kimga, qachon va qanday yuborishni siz hal qilasiz — bu ham Instagram'ning
spam siyosatiga to'qnashmaslik, ham sifatni nazorat qilish uchun muhim.

## Fayllar tuzilishi

```
ai-content-agent/
├── main.py                    # 1-bosqich pipeline (video tayyorlash)
├── video_processor.py         # Video formatlash (ffmpeg)
├── subtitle_generator.py      # Transkripsiya + subtitr (faster-whisper)
├── caption_generator.py       # AI caption/hashtag (Claude API)
├── instagram_publisher.py     # Instagram'ga avtomatik joylash
├── instagram_insights.py      # Statistika olish (Graph API)
├── performance_analyzer.py    # AI orqali statistika tahlili
├── cloud_storage.py           # Videoni R2'ga yuklab, ochiq URL olish
├── instagram_comments.py      # Kommentlarni olish/javob yozish (quyi daraja)
├── comment_monitor.py         # Komment dashboard + AI taklif javoblar
├── scheduler.py                # Postlarni oldindan rejalashtirish (navbat)
├── webapp/                     # 4-bosqich: ko'p mijozli obuna platformasi
│   └── ... (batafsil: webapp/README.md)
├── requirements.txt
├── input/                     # Xom videolaringizni shu yerga qo'ying
└── output/                    # Tayyor natijalar shu yerda chiqadi
```

## Postlarni rejalashtirish (scheduler)

```bash
# Navbatga qo'shish (ISO format vaqt bilan):
python3 scheduler.py add output/video_final.mp4 "Caption matni" "2026-09-25T18:00:00"

# Navbatni ko'rish:
python3 scheduler.py list

# Vaqti kelgan postlarni joylash (buni cron orqali muntazam chaqiring):
python3 scheduler.py run
```

Cron misoli (har 5 daqiqada tekshiradi):
```
*/5 * * * * cd /path/to/ai-content-agent && python3 scheduler.py run >> scheduler.log 2>&1
```

## Keyingi bosqichlar (hali qo'shilmagan)

- [ ] Ko'p server uchun to'liq navbat tizimi (Celery/RQ) — batafsil `webapp/README.md`da

## Muhim eslatmalar

- Birinchi ishga tushirishda `faster-whisper` model faylini internetdan
  yuklab oladi (bir necha yuz MB, faqat bir marta).
- `ANTHROPIC_API_KEY` sozlanmasa, caption generatsiya va tahlil
  bosqichlarida xatolik chiqadi.
- Instagram'ning kunlik joylash chegarasi bor: 24 soatda 100 ta post
  (`instagram_publisher.check_publishing_limit()` orqali tekshirish mumkin).
- Instagram API versiyalari muntazam yangilanadi — `instagram_publisher.py`
  va `instagram_insights.py` ichidagi `API_VERSION` ni vaqti-vaqti bilan
  developers.facebook.com dan tekshirib turing.
- Bu kodlar Meta'ning rasmiy hujjatlariga asoslangan, lekin haqiqiy
  Instagram Business akkaunt va token bilan hali sinalmagan (buni faqat
  siz o'zingizning akkauntingiz bilan tekshira olasiz).
