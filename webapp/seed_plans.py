"""
seed_plans.py
---------------
Boshlang'ich tarif rejalarini bazaga qo'shadi. Bir marta ishga tushiriladi.

Ishlatish:
    cd webapp
    python3 seed_plans.py
"""

from app.database import SessionLocal, init_db
from app import models

init_db()
db = SessionLocal()

existing = db.query(models.Plan).count()
if existing > 0:
    print(f"Bazada allaqachon {existing} ta tarif bor — o'tkazib yuborildi.")
else:
    plans = [
        models.Plan(
            name="Boshlang'ich",
            description="Oyiga 8 tagacha Reels: video formatlash, subtitr, caption, joylash",
            price_uzs=299000,
            duration_days=30,
        ),
        models.Plan(
            name="Professional",
            description="Oyiga 20 tagacha Reels + statistika tahlili + komment monitoring",
            price_uzs=599000,
            duration_days=30,
        ),
    ]
    db.add_all(plans)
    db.commit()
    print(f"{len(plans)} ta tarif qo'shildi.")

db.close()
