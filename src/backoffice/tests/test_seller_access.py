import io
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone

from src.backoffice.models import AccessScope, AuditLog, BusinessUnit, BusinessUnitMembership, TemporaryCredential
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.customers.models import Customer, CustomerBusinessRelationship
from src.salespeople.models import Salesperson


class SellerAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_backoffice_rbac()
        cls.user = get_user_model().objects.create_user(username="pedro@example.com", password="Temporary-Test-985!", email="pedro@example.com")
        cls.user.groups.add(Group.objects.get(name="SALESPERSON"))
        cls.seller = Salesperson.objects.create(user=cls.user, code="PEDRO", name="Pedro")
        cls.unit = BusinessUnit.objects.create(code="TEST", name="Test", slug="test")
        BusinessUnitMembership.objects.create(user=cls.user, business_unit=cls.unit, scope=AccessScope.OWN)
        cls.own = Customer.objects.create(legal_name="Minha carteira")
        cls.other = Customer.objects.create(legal_name="Carteira confidencial")
        CustomerBusinessRelationship.objects.create(customer=cls.own, business_unit=cls.unit, assigned_salesperson=cls.seller)
        CustomerBusinessRelationship.objects.create(customer=cls.other, business_unit=cls.unit)

    def setUp(self):
        self.client.force_login(self.user)

    def temporary(self, expired=False):
        return TemporaryCredential.objects.create(user=self.user, expires_at=timezone.now() + timedelta(hours=-1 if expired else 24))

    def test_own_customer_only_and_no_global_audit(self):
        AuditLog.objects.create(action="CREATE", module="private", object_repr="SEGREDO ADMINISTRATIVO")
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SEGREDO ADMINISTRATIVO")
        self.assertNotContains(response, "Últimos acessos")
        self.assertFalse(self.user.has_perm("backoffice.view_auditlog"))
        response = self.client.get(reverse("backoffice:customer_list"))
        self.assertContains(response, self.own.legal_name)
        self.assertNotContains(response, self.other.legal_name)
        for name in ["customer_detail", "customer_update"]:
            self.assertEqual(self.client.get(reverse(f"backoffice:{name}", args=[self.other.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("backoffice:customer_update", args=[self.other.pk]), {}).status_code, 404)

    def test_administrative_routes_and_prospecting_blocked(self):
        names = ["salesperson_list", "salesperson_create", "business_unit_list", "business_unit_create", "department_list", "department_create", "team_list", "team_create", "business_unit_membership_list", "business_unit_membership_create", "product_create", "brand_create", "category_create", "sales_intelligence_campaign_list", "sales_intelligence_campaign_create"]
        for name in names:
            for method in (self.client.get, self.client.post):
                with self.subTest(name=name, method=method):
                    self.assertEqual(method(reverse(f"backoffice:{name}")).status_code, 403)
        for name in ["product_update", "product_activate", "product_deactivate", "product_feature", "product_unfeature", "product_image_create", "product_image_delete", "salesperson_update", "business_unit_membership_update"]:
            self.assertEqual(self.client.post(reverse(f"backoffice:{name}", args=[999])).status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertEqual(self.client.get(reverse("backoffice:sales_intelligence_search_run_detail", args=[999])).status_code, 403)

    def test_temporary_password_requires_change_even_for_api(self):
        self.temporary()
        for url in [reverse("backoffice:dashboard"), reverse("backoffice:sales_intelligence_search_run_detail", args=[999]), "/admin/"]:
            self.assertRedirects(self.client.get(url), reverse("backoffice:password_change"))
        response = self.client.post(reverse("backoffice:password_change"), {"old_password": "Temporary-Test-985!", "new_password1": "Personal-Strong-9482!", "new_password2": "Personal-Strong-9482!"})
        self.assertRedirects(response, reverse("backoffice:dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Personal-Strong-9482!"))
        self.assertFalse(TemporaryCredential.objects.get(user=self.user).must_change)
        self.assertFalse(self.client.login(username=self.user.username, password="Temporary-Test-985!"))

    def test_temporary_password_cannot_be_reused(self):
        self.temporary()
        response = self.client.post(reverse("backoffice:password_change"), {"old_password": "Temporary-Test-985!", "new_password1": "Temporary-Test-985!", "new_password2": "Temporary-Test-985!"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(TemporaryCredential.objects.get(user=self.user).must_change)

    def test_expired_password_logs_out_and_denies_change(self):
        self.temporary(expired=True)
        response = self.client.get(reverse("backoffice:password_change"))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_weak_password_and_csrf_rejected(self):
        self.temporary()
        response = self.client.post(reverse("backoffice:password_change"), {"old_password": "Temporary-Test-985!", "new_password1": "123", "new_password2": "123"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(TemporaryCredential.objects.get(user=self.user).must_change)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse("backoffice:password_change"), {}).status_code, 403)


class LocalPreparationTests(TestCase):
    def run_prepare(self, path):
        # Test DB remains in-memory; only the command's configuration guard is overridden.
        database = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": settings.BASE_DIR / "seller-preparation.sqlite3"}}
        with override_settings(SETTINGS_MODULE="config.settings.local_preparation", DATABASES=database):
            call_command("prepare_pedro_local", credential_file=str(path), stdout=io.StringIO())

    def test_provisioning_and_repeat_do_not_reset_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credential.txt"
            self.run_prepare(path)
            user = get_user_model().objects.get(username="pedro@smartcontrolbrasil.com.br")
            self.assertFalse(user.is_staff or user.is_superuser)
            self.assertEqual(list(user.groups.values_list("name", flat=True)), ["SALESPERSON"])
            self.assertFalse(user.user_permissions.exists())
            self.assertEqual(user.business_unit_memberships.get().scope, AccessScope.OWN)
            self.assertEqual(user.salesperson_profile.email, user.email)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            password = path.read_text().split("Senha temporária: ")[1].splitlines()[0]
            self.assertTrue(user.check_password(password))
            self.assertNotIn(password, str(list(AuditLog.objects.values())))
            with self.assertRaises(CommandError):
                self.run_prepare(Path(directory) / "second.txt")
            user.refresh_from_db()
            self.assertTrue(user.check_password(password))

    def test_refuses_other_settings(self):
        with override_settings(SETTINGS_MODULE="config.settings.production"):
            with self.assertRaises(CommandError):
                call_command("prepare_pedro_local", credential_file="/tmp/unused.txt")

    def test_contaminated_role_rolls_back(self):
        sync_backoffice_rbac()
        Group.objects.get(name="SALESPERSON").permissions.add(Permission.objects.get(codename="add_user"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credential.txt"
            with self.assertRaises(CommandError):
                self.run_prepare(path)
            self.assertFalse(path.exists())
            self.assertFalse(get_user_model().objects.filter(username="pedro@smartcontrolbrasil.com.br").exists())

    def test_existing_credential_file_is_preserved_and_user_rolled_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credential.txt"
            path.write_text("existing secret")
            with self.assertRaises(FileExistsError):
                self.run_prepare(path)
            self.assertEqual(path.read_text(), "existing secret")
            self.assertFalse(get_user_model().objects.filter(username="pedro@smartcontrolbrasil.com.br").exists())


class CompositePermissionTests(TestCase):
    def test_missing_permission_reference_fails_closed(self):
        from src.backoffice.permissions.registry import BackofficePermission
        from src.backoffice.permissions.services import user_has_backoffice_permission

        sync_backoffice_rbac()
        user = get_user_model().objects.create_user(username="manager")
        user.groups.add(Group.objects.get(name="COMMERCIAL_MANAGER"))
        Permission.objects.filter(content_type__app_label="sales_intelligence", codename="view_searchrun").delete()
        self.assertFalse(user_has_backoffice_permission(user, BackofficePermission.SALES_INTELLIGENCE_VIEW))
