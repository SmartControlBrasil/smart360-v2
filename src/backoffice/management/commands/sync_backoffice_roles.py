from django.core.management.base import BaseCommand

from src.backoffice.permissions.registry import RESERVED_PERMISSIONS
from src.backoffice.permissions.services import sync_backoffice_rbac


class Command(BaseCommand):
    help = "Sincroniza Groups e Permissions reais do backoffice."

    def handle(self, *args, **options):
        result = sync_backoffice_rbac(stdout=self.stdout)
        if result["missing_permissions"]:
            self.stdout.write(
                self.style.WARNING(
                    "Permissões reais ausentes: " + ", ".join(sorted(set(result["missing_permissions"])))
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Backoffice roles sincronizados: "
                f"{len(result['created'])} criados, "
                f"{len(result['updated'])} atualizados, "
                f"{len(result['unchanged'])} mantidos."
            )
        )
        if RESERVED_PERMISSIONS:
            self.stdout.write(
                "Permissões reservadas para módulos futuros: "
                + ", ".join(permission.value for permission in RESERVED_PERMISSIONS)
            )
