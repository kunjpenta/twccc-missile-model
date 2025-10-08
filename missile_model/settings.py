# missile_model/settings.py
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from celery.schedules import crontab
from dotenv import load_dotenv

# ------------------------------
# Base paths & environment
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
APPEND_SLASH = True

# ------------------------------
# Core settings
# ------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "override-in-.env")
DEBUG = os.getenv("DJANGO_DEBUG", "False").strip().lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if DEBUG and not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# ------------------------------
# Installed apps
# ------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "core",
    "tewa",
]

# ------------------------------
# Middleware
# ------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # must be above CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'corsheaders.middleware.CorsMiddleware',  # Add this line at the top

]

# ------------------------------
# URLs / WSGI / ASGI
# ------------------------------
ROOT_URLCONF = "missile_model.urls"
WSGI_APPLICATION = "missile_model.wsgi.application"
# ASGI_APPLICATION = "missile_model.asgi.application"

# ------------------------------
# Templates
# ------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------
# Database
# ------------------------------


def parse_database_url(url: str) -> dict:
    """Parse PostgreSQL URL."""
    p = urlparse(url)
    if p.scheme not in ("postgres", "postgresql"):
        raise ValueError("Only postgres/postgresql URLs are supported")
    q = parse_qs(p.query)
    options = {"sslmode": q["sslmode"][0]} if "sslmode" in q else {}
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": p.path.lstrip("/"),
        "USER": p.username or "",
        "PASSWORD": p.password or "2020",
        "HOST": p.hostname or "127.0.0.1",
        "PORT": str(p.port or "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "OPTIONS": options,
    }


USE_SQLITE = os.getenv("USE_SQLITE", "False").strip().lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if USE_SQLITE:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }
elif DATABASE_URL:
    DATABASES = {"default": parse_database_url(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "missile_model_db"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "2020"),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }

# ------------------------------
# DRF & CORS
# ------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",  # file uploads
        "rest_framework.parsers.FormParser",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",  # UTC ISO8601
}

CORS_ALLOW_ALL_ORIGINS = os.getenv(
    "CORS_ALLOW_ALL_ORIGINS", "False").strip().lower() == "true"
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:4200").split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = os.getenv(
    "CORS_ALLOW_CREDENTIALS", "False").strip().lower() == "true"

# ------------------------------
# Auth / Password validation
# ------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------
# I18N / Time
# ------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ------------------------------
# Static & media
# ------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR /
                    "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------
# Security hardening
# ------------------------------
if os.getenv("DJANGO_SECURE", "False").strip().lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.getenv(
        "DJANGO_SECURE_SSL_REDIRECT", "True").strip().lower() == "true"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = os.getenv("DJANGO_REFERRER_POLICY", "same-origin")

# ------------------------------
# Logging
# ------------------------------
LOG_LEVEL = "DEBUG" if DEBUG else os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {name}: {message}", "style": "{"},
        "verbose": {"format": "{asctime} [{levelname}] {name} ({module}:{lineno}): {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple" if DEBUG else "verbose"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {"django.server": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}},
}

# ------------------------------
# Celery Beat
# ------------------------------
CELERY_BEAT_SCHEDULE = {
    "compute-threats-every-5-min": {
        "task": "tewa.tasks.periodic_compute_threats",
        "schedule": crontab(minute="*/5"),
        "args": (1,),  # scenario_id
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery Settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Redis as the message broker
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Celery Beat for periodic tasks
CELERY_BEAT_SCHEDULE = {
    'compute-threat-scores': {
        'task': 'tewa.management.commands.compute_threats',
        'schedule': 3600.0,  # Run every hour (3600 seconds)
    },
}
