import os
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-test-key-for-development")

DEBUG = True

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Мои приложения
    "django_filters",
    "drf_yasg",
    "rest_framework",
    "bot",
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


def is_running_in_docker():
    """Определяем, запущен ли код в Docker контейнере"""
    try:
        # Проверяем, существует ли файл .dockerenv
        return os.path.exists('/.dockerenv')
    except:
        return False

def get_db_host():
    """Динамически определяем DB_HOST в зависимости от окружения"""
    if is_running_in_docker():
        # Если в Docker - используем имя сервиса из docker-compose
        return 'db'
    else:
        # Если локально - используем localhost
        return os.getenv('DB_HOST', 'localhost')

def get_redis_url():
    """Динамически определяем Redis URL"""
    if is_running_in_docker():
        return 'redis://redis:6379/0'
    else:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        return f'redis://{redis_host}:{redis_port}/0'

# DB settings

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "TG_Bot_ToDo_List"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": get_db_host(),  # Используем динамическое определение
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {"Basic": {"type": "basic"}},
    "USE_SESSION_AUTH": False,
}


LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Adak"

USE_I18N = True

USE_TZ = True

# Static files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# CELERY settings

CELERY_BROKER_URL = get_redis_url()
CELERY_RESULT_BACKEND = get_redis_url()
CELERY_TIMEZONE = "America/Adak"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

if DEBUG:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

CELERY_BEAT_SCHEDULE = {
    "check-overdue-tasks-every-hour": {
        "task": "bot.tasks.check_overdue_tasks",
        "schedule": crontab(minute=0, hour="*"),
    },
    "send-daily-reminders": {
        "task": "bot.tasks.send_daily_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
}

if DEBUG:
    INSTALLED_APPS.append("corsheaders")
    MIDDLEWARE.insert(2, "corsheaders.middleware.CorsMiddleware")
    CORS_ALLOW_ALL_ORIGINS = True

    CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }

# TG settings

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

print(f"\n{'='*50}")
print(f"🚀 Django запущен в окружении: {'Docker' if is_running_in_docker() else 'Local'}")
print(f"📊 DB_HOST: {get_db_host()}")
print(f"🔗 Redis URL: {get_redis_url()}")
print(f"🌐 Telegram Bot Token: {'Установлен' if TELEGRAM_BOT_TOKEN else 'НЕ установлен!'}")
print(f"{'='*50}\n")
