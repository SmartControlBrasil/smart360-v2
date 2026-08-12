from src.backoffice.permissions.registry import BackofficeRole
from src.salespeople.models import Salesperson


def user_role_codes(user):
    if not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


def customer_scope_for_user(user):
    if getattr(user, "is_superuser", False):
        return "ALL"
    roles = user_role_codes(user)
    if BackofficeRole.SYSTEM_ADMIN.value in roles or BackofficeRole.COMMERCIAL_MANAGER.value in roles:
        return "ALL"
    if BackofficeRole.SALESPERSON.value in roles:
        return "OWN"
    if BackofficeRole.VIEWER.value in roles:
        return "ALL"
    return "NONE"


def salesperson_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.salesperson_profile
    except Salesperson.DoesNotExist:
        return None


def apply_customer_scope(queryset, user):
    scope = customer_scope_for_user(user)
    if scope == "ALL":
        return queryset
    if scope == "OWN":
        salesperson = salesperson_for_user(user)
        if salesperson is None:
            return queryset.none()
        return queryset.filter(assigned_salesperson=salesperson)
    return queryset.none()


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
