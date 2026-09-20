"""
setup_test_account.py
------------------------
FAQAT SIZNING SHAXSIY SINOVINGIZ UCHUN.

Web sahifada (http://localhost:8000/app/) ro'yxatdan o'tgan hisobingizga:
1. 365 kunlik sinov obunasini to'lovsiz faollashtiradi
2. buba_smm Instagram akkauntini ulaydi (main.py CLI uchun sozlagan
   IG_ACCESS_TOKEN/IG_USER_ID orqali — haqiqiy OAuth jarayonini chetlab o'tib,
   chunki OAuth ochiq internet manzili talab qiladi, bu esa faqat server
   internetga chiqarilgach ishlaydi)

MUHIM: bu ikkalasi ham HAQIQIY MIJOZLAR uchun emas. Haqiqiy mijoz
/subscribe orqali to'laydi va "Instagram ulash" tugmasi orqali o'z
akkauntini OAuth bilan ulaydi. Bu skript faqat SIZNING o'zingizni
sinash uchun qulaylik yaratadi.
"""

import os
import sys
from datetime import datetime, timedelta

from app.database import SessionLocal, init_db
from app import models

init_db()
db = SessionLocal()

print("=" * 50)
print("Buba — sinov hisobini sozlash")
print("=" * 50)

email = input("\nWeb sahifada ro'yxatdan o'tgan email manzilingiz: ").strip()

user = db.query(models.User).filter(models.User.email == email).first()
if not user:
    print(f"\nXATO: '{email}' bilan ro'yxatdan o'tgan foydalanuvchi topilmadi.")
    print("Avval http://localhost:8000/app/ sahifasida ro'yxatdan o'ting,")
    print("keyin bu faylni qayta ishga tushiring.")
    db.close()
    sys.exit(1)

# 1) Obuna
plan = db.query(models.Plan).first()
if not plan:
    print("\nXATO: hech qanday tarif topilmadi.")
    print("Buni tuzatish uchun avval 'python seed_plans.py' ni ishga tushiring.")
    db.close()
    sys.exit(1)

existing_active = (
    db.query(models.Subscription)
    .filter(
        models.Subscription.user_id == user.id,
        models.Subscription.status == models.SubscriptionStatus.ACTIVE,
    )
    .first()
)
if not existing_active:
    sub = models.Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=models.SubscriptionStatus.ACTIVE,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=365),
    )
    db.add(sub)
    print("\n[OK] Sinov obunasi faollashtirildi (365 kunga).")
else:
    print("\n[OK] Sizda allaqachon faol obuna bor edi.")

# 2) Instagram
access_token = os.environ.get("IG_ACCESS_TOKEN")
ig_user_id = os.environ.get("IG_USER_ID")

if access_token and ig_user_id:
    account = (
        db.query(models.InstagramAccount)
        .filter(models.InstagramAccount.user_id == user.id)
        .first()
    )
    if account:
        account.access_token = access_token
        account.ig_user_id = ig_user_id
        account.connected_at = datetime.utcnow()
    else:
        account = models.InstagramAccount(
            user_id=user.id,
            ig_user_id=ig_user_id,
            access_token=access_token,
            username="buba_smm",
        )
        db.add(account)
    print("[OK] Instagram (buba_smm) ulandi.")
else:
    print("[OGOHLANTIRISH] IG_ACCESS_TOKEN yoki IG_USER_ID topilmadi —")
    print("                Instagram ulanmadi (video joylash ishlamaydi,")
    print("                lekin video tayyorlash va caption yozish ishlaydi).")

db.commit()
db.close()

print("\n" + "=" * 50)
print("Tayyor! Brauzerda http://localhost:8000/app/ sahifasini")
print("yangilang (F5) — obuna va Instagram holati yangilanadi.")
print("=" * 50)
