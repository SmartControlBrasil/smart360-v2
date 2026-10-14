import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.backoffice.models import AuditLog, BusinessUnit, TemporaryCredential
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.backoffice.services.pedro_provisioning import EMAIL, provision_pedro
from src.backoffice.tests import test_seller_access
from src.customers.models import CustomerBusinessRelationship
from src.salespeople.models import Salesperson


class ProductionProvisioningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_backoffice_rbac()
        BusinessUnit.objects.get_or_create(code="SMART_CONTROL", defaults={"name": "Smart Control", "slug": "smart-control"})

    def test_preflight_has_no_writes_or_password_generation(self):
        with patch("src.backoffice.services.pedro_provisioning.secrets.token_urlsafe") as random:
            self.assertEqual(provision_pedro(), "would_create")
            random.assert_not_called()
        self.assertFalse(get_user_model().objects.filter(username=EMAIL).exists())
        self.assertFalse(TemporaryCredential.objects.exists())

    def test_new_password_expiry_exact_policy_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pedro.credential"
            before = timezone.now()
            self.assertEqual(provision_pedro(apply=True, credential_file=path), "created")
            user = get_user_model().objects.get(username=EMAIL)
            credential = TemporaryCredential.objects.get(user=user)
            password = path.read_text().split("Senha temporária: ")[1].splitlines()[0]
            self.assertTrue(user.check_password(password))
            self.assertTrue(86400 <= (credential.expires_at - before).total_seconds() < 86410)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(user.is_staff or user.is_superuser or user.user_permissions.exists())
            self.assertEqual(list(user.groups.values_list("name", flat=True)), ["SALESPERSON"])
            self.assertEqual(user.business_unit_memberships.get().scope, "OWN")
            self.assertEqual(provision_pedro(apply=True, credential_file=path), "unchanged")
            self.assertEqual(TemporaryCredential.objects.get(user=user).expires_at, credential.expires_at)
            user.refresh_from_db()
            self.assertTrue(user.check_password(password))
            self.assertNotIn(password, str(list(AuditLog.objects.values())))
            # After first login, a replay must not reset the personal password either.
            credential.must_change = False
            credential.save()
            self.assertEqual(provision_pedro(apply=True), "unchanged")

    def test_refuses_existing_local_or_unknown_account(self):
        get_user_model().objects.create_user(username=EMAIL, email=EMAIL)
        with self.assertRaises(CommandError):
            provision_pedro(apply=True)

    def test_conforming_account_with_local_marker_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as directory:
            provision_pedro(apply=True, credential_file=Path(directory) / "pedro.credential")
            AuditLog.objects.filter(object_repr=EMAIL).update(metadata={"local_preparation": True})
            with self.assertRaises(CommandError):
                provision_pedro(apply=True)

    def test_role_drift_and_identity_collision_fail_closed(self):
        group = Group.objects.get(name="SALESPERSON")
        group.permissions.add(Permission.objects.get(codename="add_user"))
        with self.assertRaises(CommandError):
            provision_pedro()
        sync_backoffice_rbac()  # Does not remove externally managed permissions.
        with self.assertRaises(CommandError):
            provision_pedro()
        self.assertFalse(get_user_model().objects.filter(username=EMAIL).exists())

    def test_replay_refuses_new_privileges_or_expired_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            provision_pedro(apply=True, credential_file=Path(directory) / "pedro.credential")
            user = get_user_model().objects.get(username=EMAIL)
            user.is_staff = True
            user.save()
            with self.assertRaises(CommandError):
                provision_pedro(apply=True)
            user.is_staff = False
            user.save()
            TemporaryCredential.objects.filter(user=user).update(expires_at=timezone.now())
            with self.assertRaises(CommandError):
                provision_pedro(apply=True)

    def test_file_failure_rolls_back_and_existing_secret_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pedro.credential"
            path.write_text("existing")
            with self.assertRaises(CommandError):
                provision_pedro(apply=True, credential_file=path)
            self.assertEqual(path.read_text(), "existing")
            path.unlink()
            with patch("src.backoffice.services.pedro_provisioning.os.fsync", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    provision_pedro(apply=True, credential_file=path)
            self.assertFalse(path.exists())
            self.assertFalse(get_user_model().objects.filter(username=EMAIL).exists())

    def test_command_refuses_nonproduction_settings_without_db_access(self):
        with patch("src.backoffice.management.commands.provision_pedro_production.provision_pedro") as service:
            with self.assertRaises(CommandError):
                call_command("provision_pedro_production", stdout=io.StringIO())
            service.assert_not_called()


class PreflightBackendTests(TestCase):
    setUpTestData = classmethod(test_seller_access.SellerAccessTests.setUpTestData.__func__)
    setUp = test_seller_access.SellerAccessTests.setUp

    def test_all_prospecting_routes_block_even_with_direct_permissions(self):
        from src.backoffice.urls import urlpatterns
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="sales_intelligence"))
        for pattern in urlpatterns:
            if not pattern.name.startswith("sales_intelligence_"):
                continue
            url = reverse(f"backoffice:{pattern.name}", kwargs={key: 999 for key in pattern.pattern.converters})
            statuses = [self.client.get(url).status_code, self.client.post(url).status_code]
            with self.subTest(route=pattern.name):
                self.assertIn(403, statuses)
                self.assertTrue(set(statuses) <= {403, 405})

    def test_filters_and_customer_audit_do_not_leak_other_teams(self):
        Salesperson.objects.create(code="SECRET", name="VENDEDOR SIGILOSO")
        BusinessUnit.objects.create(code="SECRET", slug="secret", name="UNIDADE SIGILOSA")
        AuditLog.objects.create(action="UPDATE", module="customers", object_type="Customer", object_id=str(self.own.pk), object_repr="EVENTO SIGILOSO")
        response = self.client.get(reverse("backoffice:customer_list"))
        self.assertNotContains(response, "VENDEDOR SIGILOSO")
        self.assertNotContains(response, "UNIDADE SIGILOSA")
        response = self.client.get(reverse("backoffice:customer_detail", args=[self.own.pk]))
        self.assertFalse(response.context["history"].exists())

    def test_shared_customer_cannot_be_edited_and_nondefault_unit_cannot_create(self):
        default_unit = BusinessUnit.objects.get(code="SMART_CONTROL")
        self.user.business_unit_memberships.update(business_unit=default_unit)
        CustomerBusinessRelationship.objects.filter(customer=self.own).update(business_unit=default_unit)
        other_unit = BusinessUnit.objects.create(code="OTHER", slug="other", name="Other")
        CustomerBusinessRelationship.objects.create(customer=self.own, business_unit=other_unit)
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(reverse("backoffice:customer_update", args=[self.own.pk])).status_code, 403)
        self.user.business_unit_memberships.update(business_unit=self.unit)
        self.assertEqual(self.client.post(reverse("backoffice:customer_create"), {}).status_code, 403)

    def test_password_change_uses_existing_login_route(self):
        self.client.logout()
        response = self.client.get(reverse("backoffice:password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("institutional:login")))

    def test_create_ignores_forged_salesperson(self):
        default_unit = BusinessUnit.objects.get(code="SMART_CONTROL")
        self.user.business_unit_memberships.update(business_unit=default_unit)
        CustomerBusinessRelationship.objects.filter(customer=self.own).update(business_unit=default_unit)
        alien = Salesperson.objects.create(code="ALIEN", name="Outro vendedor")
        response = self.client.post(reverse("backoffice:customer_create"), {
            "customer_type": "COMPANY", "legal_name": "Cliente criado no preflight",
            "status": "PROSPECT", "assigned_salesperson": alien.pk,
        })
        self.assertEqual(response.status_code, 302)
        from src.customers.models import Customer
        customer = Customer.objects.get(legal_name="Cliente criado no preflight")
        self.assertEqual(customer.assigned_salesperson_id, self.seller.pk)
        self.assertEqual(customer.business_relationships.get().assigned_salesperson_id, self.seller.pk)
