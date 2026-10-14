from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from src.backoffice.services.pedro_provisioning import provision_pedro


class Command(BaseCommand):
    help = "Preflight de Pedro em produção; só grava com --apply. Nunca imprime a senha."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--credential-file")

    def handle(self, *args, **options):
        if (settings.SETTINGS_MODULE != "config.settings.production"
                or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql"):
            raise CommandError("Este comando exige config.settings.production e PostgreSQL.")
        result = provision_pedro(apply=options["apply"], credential_file=options["credential_file"])
        self.stdout.write({
            "would_create": "Preflight válido: Pedro seria criado. Nenhuma gravação ou senha gerada.",
            "created": "Pedro provisionado; credencial nova no arquivo privado informado (0600), válida por 24 horas.",
            "unchanged": "Pedro já corresponde à política. Nenhuma alteração de senha, validade ou permissões.",
        }[result])
