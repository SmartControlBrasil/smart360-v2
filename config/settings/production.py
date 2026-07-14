from .base import *  # noqa: F403


DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],  # noqa: F405
        "USER": os.environ["POSTGRES_USER"],  # noqa: F405
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],  # noqa: F405
        "HOST": os.environ["POSTGRES_HOST"],  # noqa: F405
        "PORT": os.getenv("POSTGRES_PORT", "5432"),  # noqa: F405
        "CONN_MAX_AGE": 60,
    }
}

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
