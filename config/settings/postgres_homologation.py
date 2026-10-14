"""Disposable SCB-PEDRO-03 cluster; never consumes POSTGRES_* destination settings."""
from .base import *  # noqa: F403

_socket = Path(os.environ["SCB_HOMO_SOCKET"]).resolve()
if _socket.parent != Path("/tmp") or not _socket.name.startswith("scb-pedro-03."):
    raise RuntimeError("Use the private /tmp/scb-pedro-03.* homologation socket directory.")
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "scb_pedro03",
    "USER": "scb_homologation",
    "PASSWORD": "",
    "HOST": str(_socket),
    "PORT": "55483",
    "CONN_MAX_AGE": 0,
    "TEST": {"NAME": "test_scb_pedro03"},
}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
