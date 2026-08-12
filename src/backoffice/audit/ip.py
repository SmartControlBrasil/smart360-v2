from django.conf import settings


TRUSTED_PROXY_IP_HEADERS = (
    "HTTP_X_REAL_IP",
    "HTTP_X_FORWARDED_FOR",
)


def get_client_ip(request):
    if request is None:
        return None

    remote_addr = request.META.get("REMOTE_ADDR")
    if not getattr(settings, "BACKOFFICE_TRUST_PROXY_HEADERS", False):
        return remote_addr

    for header in TRUSTED_PROXY_IP_HEADERS:
        value = request.META.get(header, "")
        if not value:
            continue
        candidate = value.split(",", 1)[0].strip()
        if candidate:
            return candidate
    return remote_addr
