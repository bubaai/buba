@echo off
cd /d %~dp0

echo ============================================
echo   BUBA ishga tushirilmoqda
echo ============================================
echo.

echo [1/3] Zarur kutubxonalar tekshirilmoqda (birinchi marta biroz vaqt oladi)...
pip install -r requirements.txt -q

echo [2/3] Boshlang'ich tariflar tekshirilmoqda...
python seed_plans.py

echo [3/3] Server ishga tushmoqda...
echo.
echo Bir necha soniyadan so'ng brauzer avtomatik ochiladi.
echo BU OYNANI YOPMANG - Buba shu oyna orqali ishlaydi.
echo To'xtatish uchun shu oynada Ctrl+C bosing.
echo.

start "" cmd /c "timeout /t 3 >nul & start http://localhost:8000/app/"

python -m uvicorn app.main:app --port 8000

pause
