import os
from pathlib import Path
from dotenv import load_dotenv

# =====================
# BASE DIR
# =====================
BASE_DIR = Path(__file__).resolve().parent.parent

# Log dizini (parsing logları için)
(BASE_DIR / "logs").mkdir(exist_ok=True)

# .env yükle
load_dotenv(BASE_DIR / ".env")

# =====================
# SECURITY
# =====================
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-gecici-key-dev-ortami"
)

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]

# =====================
# APPLICATIONS
# =====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'ihaleler',
]

# =====================
# MIDDLEWARE
# =====================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ihale_sistemi.urls'

# =====================
# TEMPLATES
# =====================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ihale_sistemi.wsgi.application'

# =====================
# DATABASE
# =====================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =====================
# PASSWORD VALIDATION
# =====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =====================
# LOCALE
# =====================
LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3

# =====================
# STATIC FILES
# =====================
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "ihaleler" / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# =====================
# AUTH
# =====================
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================
# AI API (en az biri gerekli: dosya yükleme → kalem çıkarma)
# .env dosyasına ekleyin. Sadece OPENAI_API_KEY yeterli (cetvel + şartname eşleştirme).
# =====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# İsteğe bağlı: Kalem çıkarma için model (boşsa sırayla gemini-2.5-flash, gemini-2.0-flash denenecek)
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "").strip() or None

# =====================
# OCR (Tesseract) - Resim/tarama metin tanıma
# =====================
# Windows: Tesseract-OCR kurulu olmalı (https://github.com/UB-Mannheim/tesseract/wiki)
# .env'de TESSERACT_CMD boş bırakılırsa Windows'ta aşağıdaki varsayılan kullanılır
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == "nt" else None,
)
# OCR dil kodu: tur=Türkçe, eng=İngilizce. Birden fazla için: "tur+eng"
OCR_LANG = os.getenv("OCR_LANG", "tur")
# PSM: 6 = Tek blok metin, 3 = Tam otomatik (detay: https://github.com/tesseract-ocr/tesseract/wiki)
OCR_PSM = os.getenv("OCR_PSM", "6")

# =====================
# LOGGING - Dosya / cetvel / şartname işleme (hata payını azaltmak için)
# =====================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "parsing": {
            "format": "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "parsing_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "parsing.log",
            "formatter": "parsing",
            "encoding": "utf-8",
        },
        "parsing_console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "parsing",
        },
    },
    "loggers": {
        "ihaleler.parsing": {
            "handlers": ["parsing_file", "parsing_console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
