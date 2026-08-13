from django.db.models import F
from django.db.models import Q

from src.backoffice.models import AccessScope
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.permissions.registry import BackofficeRole
from src.salespeople.models import Salesperson


SUPPORTED_CUSTOMER_SCOPES = {AccessScope.ALL, AccessScope.DEPARTMENT, AccessScope.TEAM, AccessScope.OWN, AccessScope.NONE}


def user_role_codes(user):
    if not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


def salesperson_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.salesperson_profile
    except Salesperson.DoesNotExist:
        return None


def active_business_unit_memberships(user):
    if not getattr(user, "is_authenticated", False):
        return BusinessUnitMembership.objects.none()
    memberships = BusinessUnitMembership.objects.select_related(
        "business_unit",
        "department",
        "team",
        "team__department",
    ).filter(
        user=user,
        is_active=True,
        business_unit__is_active=True,
    )
    return memberships.filter(
        Q(scope__in=[AccessScope.ALL, AccessScope.OWN, AccessScope.NONE])
        | Q(scope=AccessScope.DEPARTMENT, department__is_active=True)
        | Q(scope=AccessScope.TEAM, department__is_active=True, team__is_active=True)
    )


def has_active_business_unit_memberships(user):
    return active_business_unit_memberships(user).exists()


def customer_scope_for_user(user):
    if getattr(user, "is_superuser", False):
        return AccessScope.ALL
    roles = user_role_codes(user)
    if BackofficeRole.SYSTEM_ADMIN.value in roles or BackofficeRole.COMMERCIAL_MANAGER.value in roles:
        return AccessScope.ALL
    if BackofficeRole.SALESPERSON.value in roles:
        return AccessScope.OWN
    if BackofficeRole.VIEWER.value in roles:
        return AccessScope.ALL
    return AccessScope.NONE


def scope_customer_relationships_for_user(queryset, user):
    if getattr(user, "is_superuser", False):
        return queryset

    roles = user_role_codes(user)
    if BackofficeRole.SYSTEM_ADMIN.value in roles:
        return queryset

    memberships = active_business_unit_memberships(user)
    if not memberships.exists():
        if BackofficeRole.COMMERCIAL_MANAGER.value in roles or BackofficeRole.VIEWER.value in roles:
            return queryset
        return queryset.none()

    scoped = queryset.none()

    all_units = memberships.filter(scope=AccessScope.ALL).values("business_unit_id")
    if memberships.filter(scope=AccessScope.ALL).exists():
        scoped = scoped | queryset.filter(business_unit_id__in=all_units)

    own_units = memberships.filter(scope=AccessScope.OWN).values("business_unit_id")
    if memberships.filter(scope=AccessScope.OWN).exists():
        salesperson = salesperson_for_user(user)
        if salesperson is not None:
            scoped = scoped | queryset.filter(
                business_unit_id__in=own_units,
                assigned_salesperson=salesperson,
            )

    department_memberships = memberships.filter(scope=AccessScope.DEPARTMENT, department__isnull=False)
    if department_memberships.exists():
        department_ids = department_memberships.values("department_id")
        department_units = department_memberships.values("business_unit_id")
        scoped = scoped | queryset.filter(
            business_unit_id__in=department_units,
            assigned_salesperson__isnull=False,
            assigned_salesperson__user__business_unit_memberships__is_active=True,
            assigned_salesperson__user__business_unit_memberships__business_unit_id=F("business_unit_id"),
            assigned_salesperson__user__business_unit_memberships__business_unit__is_active=True,
            assigned_salesperson__user__business_unit_memberships__department_id__in=department_ids,
            assigned_salesperson__user__business_unit_memberships__department__is_active=True,
        )

    team_memberships = memberships.filter(scope=AccessScope.TEAM, team__isnull=False)
    if team_memberships.exists():
        team_ids = team_memberships.values("team_id")
        team_units = team_memberships.values("business_unit_id")
        scoped = scoped | queryset.filter(
            business_unit_id__in=team_units,
            assigned_salesperson__isnull=False,
            assigned_salesperson__user__business_unit_memberships__is_active=True,
            assigned_salesperson__user__business_unit_memberships__business_unit_id=F("business_unit_id"),
            assigned_salesperson__user__business_unit_memberships__business_unit__is_active=True,
            assigned_salesperson__user__business_unit_memberships__team_id__in=team_ids,
            assigned_salesperson__user__business_unit_memberships__department__is_active=True,
            assigned_salesperson__user__business_unit_memberships__team__is_active=True,
        )

    return scoped.distinct()


def apply_customer_scope(queryset, user):
    if getattr(user, "is_superuser", False):
        return queryset

    roles = user_role_codes(user)
    if BackofficeRole.SYSTEM_ADMIN.value in roles:
        return queryset

    memberships = active_business_unit_memberships(user)
    if not memberships.exists():
        if BackofficeRole.COMMERCIAL_MANAGER.value in roles or BackofficeRole.VIEWER.value in roles:
            return queryset
        return queryset.none()

    from src.customers.models import CustomerBusinessRelationship

    relationships = scope_customer_relationships_for_user(CustomerBusinessRelationship.objects.all(), user)
    return queryset.filter(business_relationships__in=relationships).distinct()


def user_can_manage_salespeople(user):
    if getattr(user, "is_superuser", False):
        return True
    roles = user_role_codes(user)
    return BackofficeRole.SYSTEM_ADMIN.value in roles or BackofficeRole.COMMERCIAL_MANAGER.value in roles


def user_can_manage_customers(user):
    if getattr(user, "is_superuser", False):
        return True
    roles = user_role_codes(user)
    return (
        BackofficeRole.SYSTEM_ADMIN.value in roles
        or BackofficeRole.COMMERCIAL_MANAGER.value in roles
        or BackofficeRole.SALESPERSON.value in roles
    )


def user_is_salesperson_role(user):
    return BackofficeRole.SALESPERSON.value in user_role_codes(user)
