"""Isolated local preparation; never uses the configured PostgreSQL database."""
from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "seller-preparation.sqlite3"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
