from django.db import transaction

from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog
from src.backoffice.services.audit_helpers import model_snapshot
from src.customers.models import Customer


CUSTOMER_AUDIT_FIELDS = [
    "customer_type",
    "legal_name",
    "trade_name",
    "document",
    "state_registration",
    "email",
    "phone",
    "whatsapp",
    "website",
    "postal_code",
    "address_line",
    "address_number",
    "address_extra",
    "district",
    "city",
    "state",
    "notes",
    "status",
    "assigned_salesperson",
]


def create_customer(*, form, request):
    with transaction.atomic():
        customer = form.save(commit=False)
        customer.created_by = request.user
        customer.updated_by = request.user
        customer.save()
        form.save_m2m()
        AuditService.record(
            action=AuditLog.Action.CREATE,
            module="customers",
            request=request,
            actor=request.user,
            object_type="Customer",
            object_id=customer.pk,
            object_repr=str(customer),
            after_data=model_snapshot(customer, CUSTOMER_AUDIT_FIELDS),
        )
    return customer


def update_customer(*, customer, form, request):
    before_instance = Customer.objects.get(pk=customer.pk)
    before = model_snapshot(before_instance, CUSTOMER_AUDIT_FIELDS)
    with transaction.atomic():
        customer = form.save(commit=False)
        customer.updated_by = request.user
        customer.save()
        form.save_m2m()
        after = model_snapshot(customer, CUSTOMER_AUDIT_FIELDS)
        action = AuditLog.Action.UPDATE
        if before.get("status") != after.get("status"):
            if after.get("status") == Customer.Status.INACTIVE:
                action = AuditLog.Action.DEACTIVATE
            elif before.get("status") == Customer.Status.INACTIVE:
                action = AuditLog.Action.ACTIVATE
        AuditService.record(
            action=action,
            module="customers",
            request=request,
            actor=request.user,
            object_type="Customer",
            object_id=customer.pk,
            object_repr=str(customer),
            before_data=before,
            after_data=after,
        )
    return customer
