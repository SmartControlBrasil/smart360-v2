"""Explicit production provisioning; no dependency on the local preparation DB/file."""
import os
import secrets
import stat
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from src.backoffice.models import (
    AccessScope, AuditLog, BusinessUnit, BusinessUnitMembership,
    DEFAULT_BUSINESS_UNIT_CODE, TemporaryCredential,
)
from src.backoffice.permissions.registry import BackofficeRole, ROLE_DEFINITIONS
from src.backoffice.permissions.services import django_permissions_for, permission_refs
from src.salespeople.models import Salesperson

EMAIL = "pedro@smartcontrolbrasil.com.br"
PROVISIONING_MARKER = "pedro-production-v1"


def _credential_target(filename):
    if not filename:
        raise CommandError("Informe --credential-file em diretório privado externo ao checkout.")
    requested = Path(filename).absolute()
    target = requested.parent.resolve() / requested.name
    if target.is_relative_to(settings.BASE_DIR.resolve()):
        raise CommandError("Credencial deve ficar fora do checkout.")
    parent = target.parent.stat()
    if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077:
        raise CommandError("Diretório da credencial deve pertencer ao operador e ter modo 0700.")
    if target.exists() or target.is_symlink():
        raise CommandError("Arquivo de credencial já existe; não será sobrescrito.")
    return target


def _validate_existing(user, group, unit):
    if (user.username != EMAIL or user.email != EMAIL or not user.is_active
            or user.is_staff or user.is_superuser or user.user_permissions.exists()
            or set(user.groups.values_list("pk", flat=True)) != {group.pk}):
        raise CommandError("Conta existente divergente; revisão manual obrigatória, sem alteração automática.")
    seller = Salesperson.objects.filter(user=user, code="PEDRO", email=EMAIL, active=True).first()
    memberships = list(user.business_unit_memberships.all())
    if seller is None or len(memberships) != 1:
        raise CommandError("Perfil/vínculos existentes divergentes; nenhuma alteração.")
    membership = memberships[0]
    if (membership.business_unit_id != unit.pk or membership.scope != AccessScope.OWN
            or not membership.is_active or membership.department_id or membership.team_id):
        raise CommandError("Membership existente não corresponde ao escopo OWN esperado.")
    marker = AuditLog.objects.filter(object_type="User", object_id=str(user.pk), module="backoffice", metadata__provisioning=PROVISIONING_MARKER).exists()
    credential = TemporaryCredential.objects.filter(user=user).first()
    if not marker or credential is None:
        raise CommandError("Conta sem origem de provisionamento de produção; não adotar/importar credencial local.")
    if credential.must_change and credential.expires_at <= timezone.now():
        raise CommandError("Credencial expirada. Reemissão exige procedimento explícito; repetição não renova a validade.")
    return "unchanged"


def provision_pedro(*, apply=False, credential_file=None):
    """Read-only by default; replays verify the exact policy and never reset a password.

    Serialize cooperating provisioners on the existing SALESPERSON row in PostgreSQL.
    RBAC synchronization is intentionally a separate release operation.
    """
    created_file = None
    try:
        with transaction.atomic():
            groups = Group.objects.select_for_update() if apply else Group.objects
            group = groups.filter(name=BackofficeRole.SALESPERSON.value).first()
            if group is None:
                raise CommandError("SALESPERSON ausente; migre e sincronize RBAC antes.")
            required = set()
            for permission in ROLE_DEFINITIONS[BackofficeRole.SALESPERSON].permissions:
                resolved = django_permissions_for(permission)
                if len(resolved) != len(permission_refs(permission)):
                    raise CommandError("Permissão ausente; migre e sincronize RBAC antes.")
                required.update(item.pk for item in resolved)
            if set(group.permissions.values_list("pk", flat=True)) != required:
                raise CommandError("Permissões SALESPERSON divergentes; revisão/sincronização explícita necessária.")
            unit = BusinessUnit.objects.filter(code=DEFAULT_BUSINESS_UNIT_CODE, is_active=True).first()
            if unit is None:
                raise CommandError("Unidade SMART_CONTROL ativa é obrigatória; nenhuma unidade será criada.")
            User = get_user_model()
            matches = list(User.objects.filter(Q(username__iexact=EMAIL) | Q(email__iexact=EMAIL)))
            if matches:
                if len(matches) != 1:
                    raise CommandError("Identidade ambígua; revisão manual obrigatória.")
                return _validate_existing(matches[0], group, unit)
            if Salesperson.objects.filter(Q(code__iexact="PEDRO") | Q(email__iexact=EMAIL)).exists():
                raise CommandError("Vendedor já existe sem vínculo validado; revisão manual obrigatória.")
            if not apply:
                return "would_create"
            target = _credential_target(credential_file)
            user = User(username=EMAIL, email=EMAIL, first_name="Pedro", is_active=True, is_staff=False, is_superuser=False)
            password = secrets.token_urlsafe(24)
            validate_password(password, user)
            user.set_password(password)
            user.save()
            user.groups.set([group])
            Salesperson.objects.create(user=user, code="PEDRO", name="Pedro", email=EMAIL, active=True)
            BusinessUnitMembership.objects.create(user=user, business_unit=unit, scope=AccessScope.OWN)
            expires_at = timezone.now() + timedelta(hours=24)
            TemporaryCredential.objects.create(user=user, expires_at=expires_at)
            AuditLog.objects.create(action=AuditLog.Action.ROLE_CHANGED, module="backoffice", object_type="User", object_id=str(user.pk), object_repr=EMAIL, after_data={"role": "SALESPERSON", "scope": "OWN"}, metadata={"provisioning": PROVISIONING_MARKER})
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created_file = target
            with os.fdopen(fd, "w") as stream:
                stream.write(f"Login: {EMAIL}\nSenha temporária: {password}\nExpira em: {expires_at.isoformat()}\nTroca obrigatória no primeiro acesso.\n")
                stream.flush()
                os.fsync(stream.fileno())
        return "created"
    except Exception:
        if created_file is not None:
            created_file.unlink(missing_ok=True)
        raise
