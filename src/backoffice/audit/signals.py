from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.signals import user_logged_out
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog


@receiver(user_logged_in)
def record_login_success(sender, request, user, **kwargs):
    AuditService.record(
        action=AuditLog.Action.LOGIN_SUCCESS,
        module="auth",
        request=request,
        actor=user,
        object_type=user.__class__.__name__,
        object_id=user.pk,
        object_repr=user.get_username(),
        metadata={"username": user.get_username()},
    )


@receiver(user_login_failed)
def record_login_failed(sender, credentials, request, **kwargs):
    username = ""
    if credentials:
        username = credentials.get("username") or credentials.get("email") or ""
    AuditService.record(
        action=AuditLog.Action.LOGIN_FAILED,
        module="auth",
        request=request,
        actor=None,
        metadata={"username": username},
    )


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    AuditService.record(
        action=AuditLog.Action.LOGOUT,
        module="auth",
        request=request,
        actor=user if getattr(user, "is_authenticated", False) else None,
        object_type=user.__class__.__name__ if user else "",
        object_id=user.pk if user else "",
        object_repr=user.get_username() if user else "",
    )
