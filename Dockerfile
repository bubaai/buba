# Buba — Render (yoki boshqa Docker-asoslangan hosting) uchun tayyor tasvir.
# ffmpeg va barcha Python bog'liqliklari (CLI pipeline + webapp) shu yerda o'rnatiladi.

FROM python:3.11-slim

# ffmpeg — video formatlash uchun shart
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Avval faqat requirements fayllarini nusxalaymiz — shunda kod o'zgarganda
# ham Docker keshi kutubxonalarni qayta yuklamaydi (tezroq qayta deploy)
COPY requirements.txt /app/requirements.txt
COPY webapp/requirements.txt /app/webapp/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r webapp/requirements.txt

# Butun loyihani nusxalaymiz (CLI skriptlar + webapp)
COPY . /app

WORKDIR /app/webapp

# Render $PORT o'zgaruvchisini avtomatik beradi; lokal sinov uchun 8000 standart
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
