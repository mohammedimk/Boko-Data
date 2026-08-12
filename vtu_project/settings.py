"""
Django settings for vtu_project.

Production-ready settings for the VTU & Data Selling Platform.
Sensitive values are read from environment variables so real credentials
never need to be hard-coded or committed to version control.
"""
import os
from pathlib import Path


from dotenv import load_dotenv

import dj_database_url

# ------------------------------------------------------------------
# Base
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a .env file in the project root (if present) into
# os.environ, so every os.environ.get(...) call below picks them up
# automatically. In production you can skip the .env file entirely and
# set real environment variables on the server instead.
#load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / '.env', override=True)


# ------------------------------------------------------------------
# Security
# ------------------------------------------------------------------


SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-key-change-this-in-production-8f3k2m9x'
)


DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# CSRF_TRUSTED_ORIGINS = [
#     o for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o
# ]



# Hardcoded to bypass environment variable parsing issues entirely
# CSRF_TRUSTED_ORIGINS = [
#     "https://unseeing-overload-mace.ngrok-free.dev",
#     "https://*.ngrok-free.dev",
#     "https://*.ngrok-free.app",
# ]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()
]


# ------------------------------------------------------------------
# Applications
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',

    # Local
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vtu_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.wallet_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'vtu_project.wsgi.application'
ASGI_APPLICATION = 'vtu_project.asgi.application'

# ------------------------------------------------------------------
# Database
# SQLite for development. Switch to PostgreSQL in production by
# setting the DATABASE_URL-style environment variables below.
# ------------------------------------------------------------------
# if os.environ.get('POSTGRES_DB'):
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.postgresql',
#             'NAME': os.environ.get('POSTGRES_DB'),
#             'USER': os.environ.get('POSTGRES_USER'),
#             'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
#             'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
#             'PORT': os.environ.get('POSTGRES_PORT', '5432'),
#         }
#     }
# else:
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': BASE_DIR / 'db.sqlite3',
#         }
#     }




DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=True
    )
}






# ------------------------------------------------------------------
# Password validation
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Static & media files
# ------------------------------------------------------------------
# STATIC_URL = '/static/'
# STATICFILES_DIRS = [BASE_DIR / 'static']
# STATIC_ROOT = BASE_DIR / 'staticfiles'



STATIC_URL = '/static/'

# Absolute path where collectstatic will gather all static files
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Extra places for collectstatic to find static files (if you have local static folder)
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Tell WhiteNoise to compress and cache static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------------------------------------------------------
# Auth redirects
# ------------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ------------------------------------------------------------------
# Crispy forms
# ------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ------------------------------------------------------------------
# Email (used for password reset). Defaults to console backend for dev.
# ------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@vtuplatform.com')

# ------------------------------------------------------------------
# Paystack (Test Mode) configuration
# ------------------------------------------------------------------
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', 'sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', 'pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
PAYSTACK_BASE_URL = 'https://api.paystack.co'
PAYSTACK_CALLBACK_URL = os.environ.get('PAYSTACK_CALLBACK_URL', 'http://127.0.0.1:8000/wallet/verify/')

PAYSTACK_DVA_ENABLED = os.environ.get('PAYSTACK_DVA_ENABLED', 'False') == 'True'          # ADD
PAYSTACK_DVA_PREFERRED_BANK = os.environ.get('PAYSTACK_DVA_PREFERRED_BANK', 'test-bank')  # ADD
# ------------------------------------------------------------------
# CheapDataHub (VTU provider) configuration
# ------------------------------------------------------------------
CHEAPDATAHUB_API_KEY = os.environ.get('CHEAPDATAHUB_API_KEY', 'cdh_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
CHEAPDATAHUB_BASE_URL = os.environ.get('CHEAPDATAHUB_BASE_URL', 'https://cheapdatahub.com/api/v1')
# When True, the platform uses the local mock provider instead of making
# real HTTP calls. Flip to False once real CheapDataHub credentials are set.
VTU_USE_MOCK_PROVIDER = os.environ.get('VTU_USE_MOCK_PROVIDER', 'True') == 'True'
#VTU_USE_MOCK_PROVIDER=False

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'vtu_platform.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# ------------------------------------------------------------------
# Session / security hardening
# ------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


WEBAUTHN_RP_ID = os.environ.get('WEBAUTHN_RP_ID', 'boko-data.onrender.com')
WEBAUTHN_RP_NAME = 'Boko-Data'
WEBAUTHN_ORIGIN = os.environ.get('WEBAUTHN_ORIGIN', 'https://boko-data.onrender.com')
