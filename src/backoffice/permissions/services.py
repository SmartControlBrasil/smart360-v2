from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.registry import REAL_PERMISSION_MAP
from src.backoffice.permissions.registry import ROLE_DEFINITIONS


def permission_refs(permission):
    permission_key = permission if isinstance(permission, BackofficePermission) else BackofficePermission(permission)
    refs = REAL_PERMISSION_MAP.get(permission_key)
    if refs is None:
        return ()
    if isinstance(refs, tuple):
        return refs
    return (refs,)


def django_permissions_for(permission):
    permissions = []
    for ref in permission_refs(permission):
        try:
            permissions.append(Permission.objects.get(content_type__app_label=ref.app_label, codename=ref.codename))
        except Permission.DoesNotExist:
            continue
    return permissions


def real_permissions_for_role(role_definition):
    permissions = []
    for permission in role_definition.permissions:
        for django_permission in django_permissions_for(permission):
            if django_permission not in permissions:
                permissions.append(django_permission)
    return permissions


def managed_django_permissions():
    permissions = []
    for permission in REAL_PERMISSION_MAP:
        for django_permission in django_permissions_for(permission):
            if django_permission not in permissions:
                permissions.append(django_permission)
    return permissions


def sync_backoffice_rbac(stdout=None):
    managed_permissions = set(managed_django_permissions())
    result = {"created": [], "updated": [], "unchanged": [], "missing_permissions": []}

    for role in ROLE_DEFINITIONS.values():
        group, created = Group.objects.get_or_create(name=role.code.value)
        desired_permissions = set(real_permissions_for_role(role))
        missing = []
        for permission in role.permissions:
            refs = permission_refs(permission)
            if refs and not django_permissions_for(permission):
                missing.append(permission.value)
        result["missing_permissions"].extend(missing)

        current_permissions = set(group.permissions.all())
        external_permissions = current_permissions - managed_permissions
        final_permissions = external_permissions | desired_permissions

        if created:
            group.permissions.set(final_permissions)
            result["created"].append(group.name)
            action = "created"
        elif current_permissions != final_permissions:
            group.permissions.set(final_permissions)
            result["updated"].append(group.name)
            action = "updated"
        else:
            result["unchanged"].append(group.name)
            action = "unchanged"

        if stdout is not None:
            permission_labels = ", ".join(sorted(permission.codename for permission in desired_permissions)) or "no managed permissions"
            stdout.write(f"{group.name}: {action}; managed permissions: {permission_labels}")

    return result


def user_has_backoffice_permission(user, permission):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    django_permissions = django_permissions_for(permission)
    if not django_permissions:
        return False
    return all(user.has_perm(f"{perm.content_type.app_label}.{perm.codename}") for perm in django_permissions)
