import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "")
    if v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# Продакшен (VPS): задайте переменные окружения перед запуском Gunicorn, например в unit-файле:
#   Environment="DJANGO_SECRET_KEY=..."
#   Environment="DJANGO_DEBUG=false"
#   Environment="DJANGO_ALLOWED_HOSTS=example.ru,www.example.ru"
#   Environment="DJANGO_CSRF_TRUSTED_ORIGINS=https://example.ru,https://www.example.ru"
# Локально ничего не задаётся — работают значения по умолчанию ниже.

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-change-in-production",
)

DEBUG = _env_bool("DJANGO_DEBUG", True)

_allowed_raw = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
if _allowed_raw:
    ALLOWED_HOSTS: list[str] = [
        h.strip() for h in _allowed_raw.split(",") if h.strip()
    ]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

if DEBUG and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")

_csrf_origins_raw = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS: list[str] = [
    o.strip() for o in _csrf_origins_raw.split(",") if o.strip()
]

if not DEBUG:
    # За Nginx с TLS: клиентский HTTPS виден Django по заголовку от прокси.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

    _hsts = os.environ.get("DJANGO_HSTS_SECONDS", "").strip()
    if _hsts.isdigit() and int(_hsts) > 0:
        SECURE_HSTS_SECONDS = int(_hsts)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool(
            "DJANGO_HSTS_INCLUDE_SUBDOMAINS", False
        )
        SECURE_HSTS_PRELOAD = _env_bool("DJANGO_HSTS_PRELOAD", False)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "quiz",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # SQLite по умолчанию почти не ждёт блокировку — при параллельных ping/stats
        # получаем «database is locked». timeout — сколько секунд ждать lock (sqlite3).
        "OPTIONS": {
            "timeout": 30,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
