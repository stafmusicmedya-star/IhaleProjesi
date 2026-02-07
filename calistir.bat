@echo off
chcp 65001 >nul
if not exist "venv\Scripts\activate.bat" (
    echo Once kurulum_ve_migrate.bat dosyasini calistirin.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo Sunucu baslatiliyor: http://127.0.0.1:8000
python manage.py runserver
