# AI Content Agent — Obuna Platformasi (4-bosqich)

## Eng oddiy boshlash yo'li (PowerShell kerak emas!)

Agar buyruqlar bilan ishlashni xohlamasangiz, faqat ikkita faylni
**ikki marta bosing**:

1. **`Buba_ishga_tushirish.bat`** — serverni ishga tushiradi va brauzerda
   avtomatik ochadi (`http://localhost:8000/app/`). Birinchi marta ishga
   tushirganda kutubxonalarni o'rnatish sabab biroz vaqt olishi mumkin.
2. Ochilgan sahifada **"Ro'yxatdan o'tish"** orqali o'zingizga hisob oching.
3. **`Sinov_hisobini_sozlash.bat`** ni ikki marta bosing — u sizdan email
   so'raydi (2-qadamda kiritgan email), so'ng sizga **sinov obunasi** va
   **Instagram (buba_smm) ulanishi**ni avtomatik beradi (to'lov va OAuth'ni
   chetlab o'tib — bular faqat SIZNING shaxsiy sinovingiz uchun).
4. Brauzerga qaytib sahifani yangilang (F5) — endi video yuklab, Instagram'ga
   avtomatik joylashni sinab ko'rishingiz mumkin, hech qanday buyruq
   yozmasdan.

**Eslatma:** `Sinov_hisobini_sozlash.bat` faqat sizning shaxsiy sinovingiz
uchun — u to'lov va Instagram OAuth jarayonlarini chetlab o'tadi. Haqiqiy
mijozlar saytda **haqiqiy to'lov** qiladi va **o'z** Instagram akkauntini
ulaydi (buning uchun keyingi bosqichda server internetga chiqarilishi kerak
— pastdagi "Instagram bilan ulanish" bo'limiga qarang).

---

Ko'p mijozli (multi-tenant) web backend: foydalanuvchilar ro'yxatdan o'tadi,
tarif tanlaydi, **Payme** yoki **Click** orqali to'laydi, va obunasi
avtomatik faollashadi.

## Nima qiladi

- Ro'yxatdan o'tish / kirish (JWT token bilan)
- Tarif rejalarini ko'rsatish (`/plans`)
- Obuna boshlash — Payme yoki Click checkout havolasini yaratadi
- **Payme Merchant API** (JSON-RPC 2.0 protokoli) — to'lov holatini kuzatib,
  muvaffaqiyatli to'lovdan keyin obunani avtomatik faollashtiradi
- **Click Shop API** (prepare/complete, MD5 imzo tekshiruvi bilan) — xuddi
  shu vazifani Click uchun bajaradi
- **Instagram OAuth ulanishi** — har bir foydalanuvchi o'z Instagram
  professional akkauntini web orqali ulaydi (Business Login for Instagram)
- **Kontent yuklash va ishlov** — foydalanuvchi video yuklaydi, fonda
  (background task) 1-3-bosqich pipeline'i ishga tushadi (formatlash,
  subtitr, AI caption, xohlasa Instagram'ga joylash) — **faqat faol
  obunasi bo'lgan foydalanuvchilar uchun**
- **Frontend** (`frontend/index.html`) — ro'yxatdan o'tish/kirish, tarif
  tanlash, Instagram ulash, video yuklash va ishlar tarixini kuzatish
  uchun bitta sahifali ilova. Backend shu faylni `/app/` manzilida
  avtomatik xizmat qiladi — alohida build qadam kerak emas.

**Test qilindi:** to'liq oqim — ro'yxatdan o'tish → kirish → obuna
boshlash → Payme'ning uch bosqichli tranzaksiyasi (CheckPerform → Create →
Perform) → obuna faollashishi, xuddi shunday Click uchun (prepare →
complete, to'g'ri va noto'g'ri MD5 imzo bilan). Instagram OAuth oqimi
(connect → callback → token almashinuvi → akkaunt saqlash → disconnect,
ko'p foydalanuvchi izolyatsiyasi bilan) Instagram serverlarini mock qilib
sinaldi. Kontent yuklash oqimi (obuna tekshiruvi → fayl yuklash → fon
vazifasi → job holati kuzatuvi → Instagram kredensiallarining to'g'ri
uzatilishi) ham to'liq sinaldi. Frontend haqiqiy brauzerda (Playwright,
Chromium) ishga tushirilib, ro'yxatdan o'tish → dashboard oqimi va
mobil ko'rinish ekran suratlari orqali tekshirildi. Jami 36 ta avtomatik
tekshiruv — barchasi muvaffaqiyatli o'tdi.

**MUHIM cheklov:** bu simulyatsiya — haqiqiy Payme/Click serverlari bilan
emas, balki ularning rasmiy protokoliga mos ravishda qurilgan test
so'rovlari bilan tekshirildi. Productionga chiqarishdan oldin:
- Payme Business kabinetidagi **"Checkup"** vositasi orqali sinang
- Click bilan hamkorlik shartnomasi doirasida test to'lovlarini o'tkazing

## O'rnatish

```bash
cd webapp
pip install -r requirements.txt
```

## Sozlash (environment o'zgaruvchilar)

```bash
# JWT (majburiy, o'zingizning tasodifiy qatoringizni qo'ying)
export JWT_SECRET_KEY="uzun-tasodifiy-maxfiy-qator"

# Baza (ixtiyoriy — standart SQLite, production uchun Postgres tavsiya etiladi)
export DATABASE_URL="sqlite:///./webapp.db"

# Payme (https://business.payme.uz dan olinadi)
export PAYME_MERCHANT_ID="..."
export PAYME_KEY="..."

# Click (https://merchant.click.uz dan olinadi)
export CLICK_SERVICE_ID="..."
export CLICK_MERCHANT_ID="..."
export CLICK_SECRET_KEY="..."

# Instagram OAuth (Meta App Dashboard'dan, "API setup with Instagram login")
export IG_APP_ID="..."
export IG_APP_SECRET="..."
export IG_REDIRECT_URI="https://sizning-domen.uz/instagram/callback"

# Kontent pipeline uchun (1-3-bosqichdagi skriptlar ham ishlatadi)
export ANTHROPIC_API_KEY="..."
export R2_ACCOUNT_ID="..." R2_ACCESS_KEY_ID="..." R2_SECRET_ACCESS_KEY="..." \
       R2_BUCKET_NAME="..." R2_PUBLIC_BASE_URL="..."
export CONTENT_UPLOAD_DIR="uploads"   # ixtiyoriy, standart: ./uploads

# Frontend (to'lov/Instagram ulanishdan keyin foydalanuvchi ilovaga qaytishi uchun)
export FRONTEND_BASE_URL="https://sizning-domen.uz"   # ixtiyoriy, lekin tavsiya etiladi

# CORS (frontend backend bilan bir domenda bo'lsa shart emas)
export CORS_ALLOWED_ORIGINS="*"   # production'da aniq domen(lar)ni ko'rsating
```

## Ishga tushirish

```bash
python3 seed_plans.py       # boshlang'ich tariflarni bazaga qo'shadi (bir marta)
uvicorn app.main:app --reload --port 8000
```

Ilova: **http://localhost:8000/app/**
Interaktiv API hujjat: http://localhost:8000/docs

## Payme/Click kabinetida sozlash
Har ikkala to'lov tizimida ham "Merchant kabinet"da quyidagi webhook
manzillarini ko'rsatishingiz kerak (serveringiz internetga ochiq bo'lishi
shart — masalan, domenli VPS):

- **Payme**: `https://sizning-domen.uz/payments/payme`
- **Click**: 
  - Prepare: `https://sizning-domen.uz/payments/click/prepare`
  - Complete: `https://sizning-domen.uz/payments/click/complete`

## Sayt sifatida ishga tushirish — HAQIQIY LINK olish (Render.com)

Bu — Instagram'ga qo'yiladigan haqiqiy havolani olish uchun kerak bo'lgan yagona
qism. Hammasi brauzer orqali, terminal kerak emas.

**Tayyor narsa:** loyiha ildizida (`ai-content-agent/Dockerfile`) server qanday
ishga tushishini to'liq tasvirlab beruvchi fayl bor — ffmpeg, barcha
kutubxonalar, hammasi shu ichida. Render shu faylni o'qib, serverni o'zi quradi.

**Qadamlar:**
1. **github.com** da bepul hisob oching (agar yo'q bo'lsa)
2. Yangi repository yarating (masalan nomi: `buba`)
3. `ai-content-agent` papkasining **butun ichidagi** fayllarini ("Add file →
   Upload files" orqali, papkani sudrab tashlab) shu repository'ga yuklang
4. **render.com** da bepul hisob oching, GitHub bilan bog'lang
5. **"New +" → "Web Service"** → repository'ngizni tanlang. Render
   Dockerfile'ni avtomatik topadi — hech narsa sozlash shart emas
6. **"Environment"** bo'limida kamida shu ikkitasini qo'shing:
   - `ANTHROPIC_API_KEY` — sizning kalitingiz
   - `JWT_SECRET_KEY` — istalgan uzun tasodifiy so'z
   (qolgan barcha o'zgaruvchilar — R2, Payme, Click, Instagram — tayyor
   bo'lganda shu yerga xuddi shunday qo'shiladi)
7. **"Create Web Service"** — bir necha daqiqadan so'ng sizga
   `https://buba-xxxx.onrender.com` kabi **haqiqiy havola** beriladi

**Muhim eslatma:** Render'ning bepul tarifida ma'lumotlar bazasi (foydalanuvchilar,
to'lovlar) server qayta ishga tushganda o'chib ketishi mumkin — bu boshlang'ich
sinov uchun muammo emas, lekin haqiqiy mijozlar bilan ishga tushirishdan oldin
Render'ning bepul PostgreSQL xizmatiga o'tish tavsiya etiladi (kod tayyor —
faqat `DATABASE_URL` o'zgaruvchisini almashtirish kifoya).

## Admin panel

Saytga **birinchi bo'lib ro'yxatdan o'tgan hisob** (odatda siz) avtomatik
**admin** bo'ladi — boshqa hech qanday sozlash shart emas. Kirgach, yuqori
o'ng burchakda **"Admin panel"** havolasi ko'rinadi. U yerda:

- **Statistika** — jami foydalanuvchilar, faol obunalar, jami va oylik tushum
- **Tariflar va narxlar** — istalgan tarifning narxini o'zgartirish, yangi
  tarif qo'shish, tarifni faol/nofaol qilish — kod yozmasdan, to'g'ridan-to'g'ri saytda
- **Foydalanuvchilar ro'yxati** — kim ro'yxatdan o'tgan, obunasi faolmi
- **To'lovlar tarixi** — kim, qachon, qaysi usul (Payme/Click) orqali qancha to'lagani

## API oqimi (qisqacha)

```
POST /auth/register          → {email, password, full_name}
POST /auth/login             → {email, password} -> {access_token}
GET  /plans                  → mavjud tariflar ro'yxati
POST /subscribe               → {plan_id, provider} -> {payment_url}
                                (foydalanuvchi shu havola orqali to'laydi)
GET  /subscriptions/me        → foydalanuvchining obunalari va holati

GET    /instagram/connect     → Instagram ruxsat sahifasiga havola
GET    /instagram/callback    → (Instagram avtomatik chaqiradi)
GET    /instagram/me          → ulangan akkaunt holati
DELETE /instagram/disconnect  → akkaunt ulanishini bekor qilish

POST /content/upload-and-publish → video yuklash + fon pipeline
                                    (multipart: file, niche, language, publish)
                                    → {job_id, status}
GET  /content/jobs/{job_id}      → ish holati (pending/processing/done/failed)
GET  /content/jobs               → foydalanuvchining barcha ishlari
```

To'lov tugagach, Payme/Click avtomatik `/payments/payme` yoki
`/payments/click/prepare` + `/payments/click/complete` ga so'rov yuboradi
— bu qism sizdan hech qanday qo'shimcha harakat talab qilmaydi.

`/content/upload-and-publish` **faol obuna talab qiladi** (402 xatosi
qaytadi, agar yo'q bo'lsa) — bu obuna/to'lov tizimini haqiqiy mahsulot
cheklovi bilan bog'laydi.

## Fayllar tuzilishi

```
webapp/
├── app/
│   ├── main.py                    # FastAPI ilova, routerlarni birlashtiradi
│   ├── database.py                # SQLAlchemy ulanishi
│   ├── models.py                  # User, Plan, Subscription, Transaction, InstagramAccount
│   ├── schemas.py                 # API so'rov/javob shakllari
│   ├── auth.py                    # Parol xeshlash + JWT
│   ├── billing_links.py           # Payme/Click checkout havolalarini yaratish
│   └── routers/
│       ├── auth_router.py         # /auth/register, /auth/login, /auth/me
│       ├── subscription_router.py # /plans, /subscribe, /subscriptions/me
│       ├── payme_router.py        # /payments/payme (JSON-RPC)
│       ├── click_router.py        # /payments/click/prepare, /complete
│       ├── instagram_router.py    # /instagram/connect, /callback, /me, /disconnect
│       └── content_router.py      # /content/upload-and-publish, /jobs
├── seed_plans.py                  # Boshlang'ich tariflarni qo'shish skripti
├── setup_test_account.py          # Shaxsiy sinov uchun: obuna+Instagram avtomatik ulash
├── Buba_ishga_tushirish.bat       # Ikki marta bosib serverni ishga tushirish (Windows)
├── Sinov_hisobini_sozlash.bat     # Ikki marta bosib sinov hisobini sozlash (Windows)
├── frontend/
│   └── index.html                 # Bitta sahifali frontend (backend /app/ orqali xizmat qiladi)
└── requirements.txt
```

## Keyingi qadamlar (bu bosqichda qo'shilmagan)

- **Fon vazifalar navbati** — hozir FastAPI'ning oddiy BackgroundTasks
  ishlatilmoqda (bitta serverda yetarli). Ko'p server/yuqori yuklama uchun
  Celery yoki RQ kabi to'liq navbat tizimiga o'tish tavsiya etiladi.
- **Production sozlamalari** — HTTPS (Let's Encrypt), PostgreSQL,
  parolni environment'da emas, maxfiy xotira (vault) da saqlash,
  Payme/Click IP manzillarini cheklash (xavfsizlik uchun), Instagram
  access tokenlarni bazada shifrlab saqlash, `CORS_ALLOWED_ORIGINS`ni
  aniq domeningizga cheklash.
