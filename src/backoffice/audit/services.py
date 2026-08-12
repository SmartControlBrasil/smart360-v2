from src.backoffice.audit.ip import get_client_ip
from src.backoffice.models import AuditLog


SENSITIVE_METADATA_KEYS = {"password", "senha", "secret", "token", "csrfmiddlewaretoken"}


def _clean_mapping(value):
    if not isinstance(value, dict):
        return value
    clean = {}
    for key, item in value.items():
        if str(key).lower() in SENSITIVE_METADATA_KEYS:
            continue
        clean[key] = _clean_mapping(item)
    return clean


class AuditService:
    @classmethod
    def record(
        cls,
        *,
        action,
        module,
        request=None,
        actor=None,
        object_type="",
        object_id="",
        object_repr="",
        before_data=None,
        after_data=None,
        metadata=None,
    ):
        if actor is None and request is not None and getattr(request, "user", None) is not None:
            user = request.user
            if getattr(user, "is_authenticated", False):
                actor = user

        session_key = ""
        if request is not None and getattr(request, "session", None) is not None:
            session_key = request.session.session_key or ""

        return AuditLog.objects.create(
            actor=actor,
            action=getattr(action, "value", action),
            module=module,
            object_type=object_type,
            object_id=str(object_id) if object_id is not None else "",
            object_repr=str(object_repr)[:255] if object_repr else "",
            before_data=_clean_mapping(before_data),
            after_data=_clean_mapping(after_data),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request is not None else "",
            session_key=session_key,
            metadata=_clean_mapping(metadata or {}),
        )


def audit_log(**kwargs):
    return AuditService.record(**kwargs)
