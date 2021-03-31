"""
Django settings for white_rabbit project.

Generated by 'django-admin startproject' using Django 3.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path

import getconf
import os

BASE_DIR = Path(__file__).resolve().parent.parent


config = getconf.ConfigGetter(
    "myproj",
    ["local_settings.conf", "/etc/telescoop/white-rabbit/backend-settings.conf"],
)

IS_LOCAL_DEV = bool(os.environ.get("TELESCOOP_DEV"))
DEBUG = IS_LOCAL_DEV

if IS_LOCAL_DEV:
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = "9cang=0bgw9jfnroblq6rv%7kk$s-6*%^7t^(e08nrqj-dj@#6"
    ALLOWED_HOSTS = []
else:
    SECRET_KEY = config.getstr("security.secret_key")
    ALLOWED_HOSTS = config.getlist("security.allowed_hosts")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "white_rabbit",
    "debug_toolbar",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "rollbar.contrib.django.middleware.RollbarNotifierMiddleware",
]

ROOT_URLCONF = "white_rabbit.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "white_rabbit.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "fr-fr"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"

# EMAIL
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

if not IS_LOCAL_DEV:
    ROLLBAR = {
        "access_token": "0009e4c34f6944dfb998246538f82830",
        "environment": "development" if DEBUG else "production",
        "root": BASE_DIR,
    }
    import rollbar

    rollbar.init(**ROLLBAR)
