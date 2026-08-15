"""
Django settings for config project.
"""

import os
import urllib.parse
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# En producción (Vercel u otro hosting) se configuran por variable de
# entorno. Localmente, sin nada seteado, corre en modo dev con SQLite.
DEBUG = os.environ.get("DEBUG", "1") == "1"

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-0esi=9p4c0l=*+4a_36jmiq#9&wd9%^+&xzm2*xd)+wafe99@k" if DEBUG else "",
)
if not SECRET_KEY:
    raise RuntimeError("Falta la variable de entorno SECRET_KEY en producción (DEBUG=0).")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS += [".vercel.app", "localhost", "127.0.0.1"]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
CSRF_TRUSTED_ORIGINS += ["https://*.vercel.app"]

# Vercel (y la mayoría de los PaaS) terminan TLS antes de la app y
# reenvían por HTTP interno con este header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tenants",
    "staff",
    "catalog",
    "appointments",
    "reviews",
    "dashboard",
    "webbooking",
    "payments",
    "whatsapp_bot",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "tenants.middleware.TenantResolutionMiddleware",
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# DATABASE_URL (Postgres) para producción; sin esa variable, SQLite local.

if os.environ.get("DATABASE_URL"):
    _db_url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_url.path.lstrip("/"),
            "USER": _db_url.username,
            "PASSWORD": _db_url.password,
            "HOST": _db_url.hostname,
            "PORT": _db_url.port,
            "OPTIONS": {"sslmode": "require"} if not DEBUG else {},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-ar"

TIME_ZONE = "America/Argentina/Buenos_Aires"

USE_I18N = True

USE_TZ = True

# URL pública del sitio (sin barra final). Se usa para armar links de pago
# y de reseñas desde contextos sin request: el bot de WhatsApp y los
# comandos de cron (recordatorios, solicitud de reseñas).
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://localhost:8000")

# Secreto compartido para autenticar los pings de cron (Vercel Cron u
# otro scheduler) contra /cron/enviar-recordatorios/ y /cron/solicitar-resenas/.
CRON_SECRET = os.environ.get("CRON_SECRET", "")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

# WhiteNoise sirve los estáticos (sobre todo el CSS/JS del admin de
# Django) directamente desde dentro de la app WSGI, sin necesitar un
# paso de build separado ni un servidor de estáticos aparte — no hay que
# confiar en que el pipeline de build del hosting corra collectstatic.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
