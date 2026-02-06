import os
from pathlib import Path

# Proje dizini (Ana klasör)
BASE_DIR = Path(__file__).resolve().parent.parent

# Güvenlik Ayarları
SECRET_KEY = 'django-insecure-l#-3ge-t9v3-mka*8g2@%c7vvb^%5*93ieq%q4e^4!7v$^gc25'
DEBUG = True
ALLOWED_HOSTS = []

# Uygulama Tanımlamaları
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Sayıları formatlamak (1.000 gibi) için eklendi
    'ihaleler',  # Senin uygulaman
]

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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ihale_sistemi.wsgi.application'

# Veritabanı
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Şifre Doğrulama
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Dil ve Zaman Ayarları
LANGUAGE_CODE = 'tr-tr'  # Türkçe yapıldı
TIME_ZONE = 'Europe/Istanbul'  # Türkiye saati yapıldı
USE_I18N = True
USE_TZ = True

# Sayı ve tarih formatlarının Türkiye standartlarında (noktalı) görünmesi için:
USE_L10N = True 
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3

# --- STATİK DOSYA AYARLARI ---
STATIC_URL = 'static/'

# Django'nun statik dosyaları (logo, css vb.) arayacağı klasör
STATICFILES_DIRS = [
    BASE_DIR / "ihaleler" / "static",
]

# Giriş ve Çıkış Yönlendirmeleri
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'