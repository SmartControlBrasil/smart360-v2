from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog
from src.backoffice.models import BusinessUnit
from src.backoffice.models import DEFAULT_BUSINESS_UNIT_CODE
from src.backoffice.models import DEFAULT_BUSINESS_UNIT_NAME
from src.backoffice.models import DEFAULT_BUSINESS_UNIT_SLUG
from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.services import user_has_backoffice_permission
from src.backoffice.services.audit_helpers import model_snapshot
from src.backoffice.services.scopes import scope_customer_relationships_for_user
from src.customers.models import Customer
from src.customers.models import CustomerAssignmentTransfer
from src.customers.models import CustomerBusinessRelationship
from src.salespeople.models import Salesperson


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


def default_business_unit():
    business_unit, _ = BusinessUnit.objects.get_or_create(
        code=DEFAULT_BUSINESS_UNIT_CODE,
        defaults={
            "name": DEFAULT_BUSINESS_UNIT_NAME,
            "slug": DEFAULT_BUSINESS_UNIT_SLUG,
            "is_active": True,
        },
    )
    return business_unit


def sync_default_customer_relationship(*, customer, request=None):
    actor = getattr(request, "user", None) if request is not None else None
    relationship, created = CustomerBusinessRelationship.objects.get_or_create(
        customer=customer,
        business_unit=default_business_unit(),
        defaults={
            "assigned_salesperson": customer.assigned_salesperson,
            "status": customer.status,
            "created_by": actor if getattr(actor, "is_authenticated", False) else customer.created_by,
            "updated_by": actor if getattr(actor, "is_authenticated", False) else customer.updated_by,
        },
    )
    if not created:
        relationship.assigned_salesperson = customer.assigned_salesperson
        relationship.status = customer.status
        if getattr(actor, "is_authenticated", False):
            relationship.updated_by = actor
        elif customer.updated_by_id:
            relationship.updated_by = customer.updated_by
        relationship.save(update_fields=["assigned_salesperson", "status", "updated_by", "updated_at"])
    return relationship


def create_customer(*, form, request):
    with transaction.atomic():
        customer = form.save(commit=False)
        customer.created_by = request.user
        customer.updated_by = request.user
        customer.save()
        form.save_m2m()
        sync_default_customer_relationship(customer=customer, request=request)
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
        sync_default_customer_relationship(customer=customer, request=request)
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


TRANSFER_AUDIT_FIELDS = ["relationship", "previous_salesperson", "new_salesperson", "transferred_by", "reason", "transferred_at"]


def valid_salespeople_for_relationship(relationship):
    return Salesperson.objects.select_related("user").filter(
        active=True,
        user__isnull=False,
        user__business_unit_memberships__business_unit=relationship.business_unit,
        user__business_unit_memberships__is_active=True,
        user__business_unit_memberships__business_unit__is_active=True,
    ).filter(
        Q(user__business_unit_memberships__scope__in=["ALL", "OWN"])
        | Q(user__business_unit_memberships__scope="DEPARTMENT", user__business_unit_memberships__department__is_active=True)
        | Q(user__business_unit_memberships__scope="TEAM", user__business_unit_memberships__department__is_active=True, user__business_unit_memberships__team__is_active=True)
    ).distinct().order_by("name")


def user_can_transfer_customer_relationship(*, user, relationship):
    if not user_has_backoffice_permission(user, BackofficePermission.CUSTOMERS_TRANSFER_ASSIGNMENT):
        return False
    if getattr(user, "is_superuser", False):
        return True
    scoped = scope_customer_relationships_for_user(CustomerBusinessRelationship.objects.filter(pk=relationship.pk), user)
    return scoped.exists()


def transfer_customer_relationship(*, relationship, new_salesperson, actor, reason, request=None):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Informe o motivo da transferência."})
    if new_salesperson is None:
        raise ValidationError({"new_salesperson": "Informe o novo responsável."})
    if not getattr(new_salesperson, "active", False):
        raise ValidationError({"new_salesperson": "O novo responsável precisa estar ativo."})
    if new_salesperson.user_id is None:
        raise ValidationError({"new_salesperson": "O novo responsável precisa ter usuário vinculado e acesso por unidade."})

    with transaction.atomic():
        locked_relationship = CustomerBusinessRelationship.objects.select_for_update(of=("self",)).select_related(
            "customer",
            "business_unit",
            "assigned_salesperson",
        ).get(pk=relationship.pk)
        if not user_can_transfer_customer_relationship(user=actor, relationship=locked_relationship):
            raise PermissionDenied("Você não tem permissão para transferir este relacionamento.")
        if not valid_salespeople_for_relationship(locked_relationship).filter(pk=new_salesperson.pk).exists():
            raise ValidationError({"new_salesperson": "O novo responsável não possui acesso ativo nesta unidade de negócio."})
        previous_salesperson = locked_relationship.assigned_salesperson
        if previous_salesperson_id := getattr(previous_salesperson, "pk", None):
            if previous_salesperson_id == new_salesperson.pk:
                raise ValidationError({"new_salesperson": "Escolha um responsável diferente do atual."})
        else:
            raise ValidationError({"new_salesperson": "A transferência formal exige um responsável atual."})

        locked_relationship.assigned_salesperson = new_salesperson
        locked_relationship.updated_by = actor if getattr(actor, "is_authenticated", False) else locked_relationship.updated_by
        locked_relationship.save(update_fields=["assigned_salesperson", "updated_by", "updated_at"])

        if locked_relationship.business_unit.code == DEFAULT_BUSINESS_UNIT_CODE:
            locked_relationship.customer.assigned_salesperson = new_salesperson
            locked_relationship.customer.updated_by = actor if getattr(actor, "is_authenticated", False) else locked_relationship.customer.updated_by
            locked_relationship.customer.save(update_fields=["assigned_salesperson", "updated_by", "updated_at"])

        transfer = CustomerAssignmentTransfer.objects.create(
            relationship=locked_relationship,
            previous_salesperson=previous_salesperson,
            new_salesperson=new_salesperson,
            transferred_by=actor if getattr(actor, "is_authenticated", False) else None,
            reason=reason,
            metadata={
                "customer_id": locked_relationship.customer_id,
                "business_unit_id": locked_relationship.business_unit_id,
                "business_unit_code": locked_relationship.business_unit.code,
            },
        )
        AuditService.record(
            action=AuditLog.Action.UPDATE,
            module="customers.assignment_transfers",
            request=request,
            actor=actor,
            object_type="CustomerAssignmentTransfer",
            object_id=transfer.pk,
            object_repr=str(transfer),
            before_data={
                "relationship": locked_relationship.pk,
                "customer": locked_relationship.customer_id,
                "business_unit": locked_relationship.business_unit_id,
                "assigned_salesperson": previous_salesperson.pk,
            },
            after_data={
                "relationship": locked_relationship.pk,
                "customer": locked_relationship.customer_id,
                "business_unit": locked_relationship.business_unit_id,
                "assigned_salesperson": new_salesperson.pk,
                "reason": reason,
            },
            metadata={"transfer_id": transfer.pk},
        )
        return transfer
