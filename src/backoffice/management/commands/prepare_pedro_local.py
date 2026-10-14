"""Prepare Pedro only in the disposable local SQLite database."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from src.backoffice.models import (
    AccessScope, AuditLog, BusinessUnit, BusinessUnitMembership, TemporaryCredential,
    DEFAULT_BUSINESS_UNIT_CODE, DEFAULT_BUSINESS_UNIT_NAME, DEFAULT_BUSINESS_UNIT_SLUG,
)
from src.backoffice.permissions.registry import BackofficeRole, ROLE_DEFINITIONS
from src.backoffice.permissions.services import real_permissions_for_role, sync_backoffice_rbac
from src.salespeople.models import Salesperson

EMAIL = "pedro@smartcontrolbrasil.com.br"


class Command(BaseCommand):
    help = "Prepara Pedro exclusivamente no SQLite local isolado; não imprime a senha."

    def add_arguments(self, parser):
        parser.add_argument("--credential-file", required=True)

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]
        if (settings.SETTINGS_MODULE != "config.settings.local_preparation"
                or database["ENGINE"] != "django.db.backends.sqlite3"
                or Path(database["NAME"]).resolve() != (settings.BASE_DIR / "seller-preparation.sqlite3").resolve()):
            raise CommandError("Use somente --settings=config.settings.local_preparation.")
        requested = Path(options["credential_file"]).absolute()
        target = requested.parent.resolve() / requested.name
        # Keep secrets outside the checkout and never overwrite an existing file/symlink.
        if target.is_relative_to(settings.BASE_DIR.resolve()):
            raise CommandError("A credencial deve ficar fora do repositório.")
        created_file = False
        try:
            with transaction.atomic():
                User = get_user_model()
                if User.objects.filter(username__iexact=EMAIL).exists() or User.objects.filter(email__iexact=EMAIL).exists():
                    raise CommandError("Pedro já existe: nenhuma senha ou permissão foi alterada.")
                if Salesperson.objects.filter(code="PEDRO").exists() or Salesperson.objects.filter(email__iexact=EMAIL).exists():
                    raise CommandError("Há um vendedor correspondente; revise o vínculo antes de continuar.")
                result = sync_backoffice_rbac()
                if result["missing_permissions"]:
                    raise CommandError("Permissões ausentes; aplique as migrações locais.")
                group = Group.objects.get(name=BackofficeRole.SALESPERSON.value)
                expected = set(real_permissions_for_role(ROLE_DEFINITIONS[BackofficeRole.SALESPERSON]))
                if set(group.permissions.all()) != expected:
                    raise CommandError("SALESPERSON contém permissões externas; revise antes de provisionar.")
                user = User(username=EMAIL, email=EMAIL, first_name="Pedro", is_active=True, is_staff=False, is_superuser=False)
                password = secrets.token_urlsafe(24)
                validate_password(password, user)
                user.set_password(password)
                user.save()
                user.groups.set([group])
                salesperson = Salesperson.objects.create(user=user, code="PEDRO", name="Pedro", email=EMAIL, active=True)
                unit, _ = BusinessUnit.objects.get_or_create(code=DEFAULT_BUSINESS_UNIT_CODE, defaults={"name": DEFAULT_BUSINESS_UNIT_NAME, "slug": DEFAULT_BUSINESS_UNIT_SLUG})
                if not unit.is_active:
                    raise CommandError("Unidade Smart Control inativa.")
                BusinessUnitMembership.objects.create(user=user, business_unit=unit, scope=AccessScope.OWN)
                expires = timezone.now() + timedelta(hours=24)
                TemporaryCredential.objects.create(user=user, expires_at=expires)
                AuditLog.objects.create(action=AuditLog.Action.ROLE_CHANGED, module="backoffice", object_type="User", object_id=str(user.pk), object_repr=EMAIL, after_data={"role": "SALESPERSON", "scope": "OWN", "salesperson_id": salesperson.pk}, metadata={"local_preparation": True})
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created_file = True
                with os.fdopen(fd, "w") as stream:
                    stream.write(f"AMBIENTE LOCAL ISOLADO\nLogin: {EMAIL}\nSenha temporária: {password}\nExpira em: {expires.isoformat()}\nTroca obrigatória no primeiro acesso.\n")
        except Exception:
            if created_file:
                target.unlink(missing_ok=True)
            raise
        self.stdout.write(self.style.SUCCESS(f"Pedro preparado localmente. Credencial em {target} (0600)."))
