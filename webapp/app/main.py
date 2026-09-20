"""
main.py
---------
FastAPI ilovasining kirish nuqtasi. Barcha routerlarni birlashtiradi va
frontend'ni (/app) statik fayl sifatida xizmat qiladi.

Ishga tushirish:
    uvicorn app.main:app --reload --port 8000

Ilova: http://localhost:8000/app/
Interaktiv API hujjat (Swagger UI): http://localhost:8000/docs
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import auth_router, subscription_router, payme_router, click_router, instagram_router, content_router, admin_router

app = FastAPI(
    title="Buba",
    description="Shaxsiy brend/kichik biznes uchun AI kontent agenti — obuna asosida",
    version="0.1.0",
)

# CORS: frontend backend bilan bir domenda joylashsa shart emas, lekin
# alohida domenda joylashtirilsa (masalan statik hosting) kerak bo'ladi.
# Production'da "*" o'rniga aniq domeningizni ko'rsating.
allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth_router.router)
app.include_router(subscription_router.router)
app.include_router(payme_router.router)
app.include_router(click_router.router)
app.include_router(instagram_router.router)
app.include_router(content_router.router)
app.include_router(admin_router.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "ai-content-agent-webapp"}


_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
