@echo off
chcp 65001 >nul
echo ============================================
echo  Ihale Projesi - Kurulum ve Migrate
echo ============================================
echo.

REM Sanal ortam yoksa oluştur
if not exist "venv" (
    echo [1/3] Sanal ortam olusturuluyor...
    python -m venv venv
    if errorlevel 1 (
        echo HATA: venv olusturulamadi. Python yuklu mu? python --version ile kontrol edin.
        pause
        exit /b 1
    )
    echo     Sanal ortam olusturuldu.
) else (
    echo [1/3] Sanal ortam zaten var.
)
echo.

REM Sanal ortamı aktive et ve paketleri kur
echo [2/3] Paketler yukleniyor (Django vb.)...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
if errorlevel 1 (
    echo HATA: pip install basarisiz.
    pause
    exit /b 1
)
echo     Paketler yuklendi.
echo.

REM Migrate çalıştır
echo [3/3] Veritabani guncelleniyor (migrate)...
python manage.py migrate
if errorlevel 1 (
    echo HATA: migrate basarisiz.
    pause
    exit /b 1
)
echo.
echo ============================================
echo  Tamamlandi.
echo  Sunucuyu baslatmak icin: calistir.bat
echo  veya: venv\Scripts\activate  sonra  python manage.py runserver
echo ============================================
pause
