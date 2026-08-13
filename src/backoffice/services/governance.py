from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog
from src.backoffice.models import BusinessUnit
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.models import Department
from src.backoffice.models import Team
from src.backoffice.services.audit_helpers import model_snapshot


BUSINESS_UNIT_AUDIT_FIELDS = ["name", "code", "slug", "is_active"]
DEPARTMENT_AUDIT_FIELDS = ["business_unit", "name", "code", "slug", "is_active"]
TEAM_AUDIT_FIELDS = ["department", "name", "code", "slug", "is_active"]
MEMBERSHIP_AUDIT_FIELDS = ["user", "business_unit", "department", "team", "scope", "is_active"]


def _action_for_active_change(before_data, after_data):
    if before_data and before_data.get("is_active") is True and after_data.get("is_active") is False:
        return AuditLog.Action.DEACTIVATE
    if before_data and before_data.get("is_active") is False and after_data.get("is_active") is True:
        return AuditLog.Action.ACTIVATE
    return AuditLog.Action.UPDATE


def create_business_unit(*, form, request):
    unit = form.save(commit=False)
    unit.save()
    AuditService.record(
        action=AuditLog.Action.CREATE,
        module="backoffice.business_units",
        request=request,
        object_type="BusinessUnit",
        object_id=unit.pk,
        object_repr=unit,
        after_data=model_snapshot(unit, BUSINESS_UNIT_AUDIT_FIELDS),
    )
    return unit


def update_business_unit(*, business_unit, form, request):
    original = BusinessUnit.objects.get(pk=business_unit.pk)
    before_data = model_snapshot(original, BUSINESS_UNIT_AUDIT_FIELDS)
    unit = form.save()
    after_data = model_snapshot(unit, BUSINESS_UNIT_AUDIT_FIELDS)
    AuditService.record(
        action=_action_for_active_change(before_data, after_data),
        module="backoffice.business_units",
        request=request,
        object_type="BusinessUnit",
        object_id=unit.pk,
        object_repr=unit,
        before_data=before_data,
        after_data=after_data,
    )
    return unit



def create_department(*, form, request):
    department = form.save(commit=False)
    department.save()
    AuditService.record(
        action=AuditLog.Action.CREATE,
        module="backoffice.departments",
        request=request,
        object_type="Department",
        object_id=department.pk,
        object_repr=department,
        after_data=model_snapshot(department, DEPARTMENT_AUDIT_FIELDS),
    )
    return department


def update_department(*, department, form, request):
    original = Department.objects.select_related("business_unit").get(pk=department.pk)
    before_data = model_snapshot(original, DEPARTMENT_AUDIT_FIELDS)
    department = form.save()
    after_data = model_snapshot(department, DEPARTMENT_AUDIT_FIELDS)
    AuditService.record(
        action=_action_for_active_change(before_data, after_data),
        module="backoffice.departments",
        request=request,
        object_type="Department",
        object_id=department.pk,
        object_repr=department,
        before_data=before_data,
        after_data=after_data,
    )
    return department


def create_team(*, form, request):
    team = form.save(commit=False)
    team.save()
    AuditService.record(
        action=AuditLog.Action.CREATE,
        module="backoffice.teams",
        request=request,
        object_type="Team",
        object_id=team.pk,
        object_repr=team,
        after_data=model_snapshot(team, TEAM_AUDIT_FIELDS),
    )
    return team


def update_team(*, team, form, request):
    original = Team.objects.select_related("department", "department__business_unit").get(pk=team.pk)
    before_data = model_snapshot(original, TEAM_AUDIT_FIELDS)
    team = form.save()
    after_data = model_snapshot(team, TEAM_AUDIT_FIELDS)
    AuditService.record(
        action=_action_for_active_change(before_data, after_data),
        module="backoffice.teams",
        request=request,
        object_type="Team",
        object_id=team.pk,
        object_repr=team,
        before_data=before_data,
        after_data=after_data,
    )
    return team


def create_membership(*, form, request):
    membership = form.save(commit=False)
    membership.save()
    AuditService.record(
        action=AuditLog.Action.CREATE,
        module="backoffice.business_unit_memberships",
        request=request,
        object_type="BusinessUnitMembership",
        object_id=membership.pk,
        object_repr=membership,
        after_data=model_snapshot(membership, MEMBERSHIP_AUDIT_FIELDS),
    )
    return membership


def update_membership(*, membership, form, request):
    original = BusinessUnitMembership.objects.select_related("user", "business_unit", "department", "team").get(pk=membership.pk)
    before_data = model_snapshot(original, MEMBERSHIP_AUDIT_FIELDS)
    membership = form.save()
    after_data = model_snapshot(membership, MEMBERSHIP_AUDIT_FIELDS)
    action = _action_for_active_change(before_data, after_data)
    if action == AuditLog.Action.UPDATE and any(before_data.get(field) != after_data.get(field) for field in ["scope", "department", "team"]):
        action = AuditLog.Action.PERMISSION_CHANGED
    AuditService.record(
        action=action,
        module="backoffice.business_unit_memberships",
        request=request,
        object_type="BusinessUnitMembership",
        object_id=membership.pk,
        object_repr=membership,
        before_data=before_data,
        after_data=after_data,
    )
    return membership


def visible_customer_relationships_for_user(*, customer, user):
    from src.backoffice.services.scopes import scope_customer_relationships_for_user
    from src.customers.models import CustomerBusinessRelationship

    relationships = CustomerBusinessRelationship.objects.select_related(
        "business_unit",
        "assigned_salesperson",
        "assigned_salesperson__user",
    ).filter(customer=customer)
    return scope_customer_relationships_for_user(relationships, user)
