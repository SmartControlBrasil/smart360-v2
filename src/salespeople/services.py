from django.db import transaction

from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog
from src.backoffice.services.audit_helpers import model_snapshot
from src.salespeople.models import Salesperson


SALESPERSON_AUDIT_FIELDS = ["user", "code", "name", "email", "phone", "whatsapp", "active", "notes"]


def create_salesperson(*, form, request):
    with transaction.atomic():
        salesperson = form.save()
        AuditService.record(
            action=AuditLog.Action.CREATE,
            module="salespeople",
            request=request,
            actor=request.user,
            object_type="Salesperson",
            object_id=salesperson.pk,
            object_repr=str(salesperson),
            after_data=model_snapshot(salesperson, SALESPERSON_AUDIT_FIELDS),
        )
    return salesperson


def update_salesperson(*, salesperson, form, request):
    before_instance = Salesperson.objects.get(pk=salesperson.pk)
    before = model_snapshot(before_instance, SALESPERSON_AUDIT_FIELDS)
    with transaction.atomic():
        salesperson = form.save()
        after = model_snapshot(salesperson, SALESPERSON_AUDIT_FIELDS)
        action = AuditLog.Action.UPDATE
        if before.get("active") != after.get("active"):
            action = AuditLog.Action.ACTIVATE if after.get("active") else AuditLog.Action.DEACTIVATE
        AuditService.record(
            action=action,
            module="salespeople",
            request=request,
            actor=request.user,
            object_type="Salesperson",
            object_id=salesperson.pk,
            object_repr=str(salesperson),
            before_data=before,
            after_data=after,
        )
    return salesperson
