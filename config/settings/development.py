from .base import *  # noqa: F403


DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "smart360_v2"),  # noqa: F405
        "USER": os.getenv("POSTGRES_USER", "smart360_v2"),  # noqa: F405
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),  # noqa: F405
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),  # noqa: F405
        "PORT": os.getenv("POSTGRES_PORT", "5432"),  # noqa: F405
    }
}
