@echo off
cd /d %~dp0

echo Bu fayl web sahifada ro'yxatdan o'tgan hisobingizga
echo sinov obunasi va Instagram (buba_smm) ulanishini beradi.
echo.
echo MUHIM: avval http://localhost:8000/app/ sahifasida
echo "Ro'yxatdan o'tish" orqali hisob ochib bo'lgan bo'lishingiz kerak.
echo.

python setup_test_account.py

pause
