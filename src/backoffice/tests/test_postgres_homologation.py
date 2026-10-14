"""SCB-PEDRO-03: real PostgreSQL locks and reversible DDL on synthetic data."""
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from src.backoffice.models import BusinessUnit, TemporaryCredential
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.backoffice.services.pedro_provisioning import EMAIL, provision_pedro


@skipUnless(connection.vendor == "postgresql", "Requires isolated PostgreSQL")
class PostgresHomologationTests(TransactionTestCase):
    def setUp(self):
        sync_backoffice_rbac()
        BusinessUnit.objects.get_or_create(code="SMART_CONTROL", defaults={"name": "Synthetic unit", "slug": "smart-control"})

    def test_concurrent_provisioning_serializes_and_does_not_rotate_password(self):
        barrier = Barrier(2)
        with tempfile.TemporaryDirectory() as directory:
            def worker(index):
                connections.close_all()
                try:
                    barrier.wait(timeout=10)
                    return provision_pedro(apply=True, credential_file=Path(directory) / f"worker-{index}.credential")
                finally:
                    connections.close_all()

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(worker, index) for index in range(2)]
                results = [future.result(timeout=30) for future in futures]
            self.assertCountEqual(results, ["created", "unchanged"])
            user = get_user_model().objects.get(username=EMAIL)
            self.assertEqual(user.business_unit_memberships.count(), 1)
            self.assertEqual(TemporaryCredential.objects.filter(user=user).count(), 1)
            files = list(Path(directory).glob("*.credential"))
            self.assertEqual(len(files), 1)
            password = files[0].read_text().split("Senha temporária: ")[1].splitlines()[0]
            self.assertTrue(user.check_password(password))

    def test_backoffice_0004_can_reverse_and_reapply_without_changing_existing_user(self):
        user = get_user_model().objects.create_user(username="synthetic-existing-user")
        original_password = user.password
        previous = [("backoffice", "0003_department_businessunitmembership_department_team_and_more")]
        current = [("backoffice", "0004_alter_auditlog_options_temporarycredential")]
        try:
            MigrationExecutor(connection).migrate(previous)
            self.assertNotIn("backoffice_temporarycredential", connection.introspection.table_names())
        finally:
            MigrationExecutor(connection).migrate(current)
        self.assertIn("backoffice_temporarycredential", connection.introspection.table_names())
        user.refresh_from_db()
        self.assertEqual(user.password, original_password)
        self.assertFalse(TemporaryCredential.objects.filter(user=user).exists())
