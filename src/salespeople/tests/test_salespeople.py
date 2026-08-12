from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from src.backoffice.models import AuditLog
from src.backoffice.permissions.registry import BackofficeRole
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.customers.models import Customer
from src.salespeople.models import Salesperson


class SalespersonTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_backoffice_rbac()
        cls.user_model = get_user_model()

    def user(self, username, role=None, **kwargs):
        user = self.user_model.objects.create_user(username=username, password="SenhaTeste123!Segura", **kwargs)
        if role:
            user.groups.add(Group.objects.get(name=role.value))
        return user


class SalespersonModelTests(SalespersonTestCase):
    def test_salesperson_creation_and_user_link(self):
        user = self.user("seller-user")
        salesperson = Salesperson.objects.create(user=user, code="S001", name="Maria", email="maria@example.com")

        self.assertEqual(str(salesperson), "Maria")
        self.assertEqual(salesperson.user, user)

    def test_active_user_link_cannot_be_duplicated(self):
        user = self.user("dup-user")
        Salesperson.objects.create(user=user, code="S001", name="Um")
        duplicate = Salesperson(user=user, code="S002", name="Dois")

        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class SalespersonBackofficeTests(SalespersonTestCase):
    def manager_login(self):
        user = self.user("manager", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.client.force_login(user)
        return user

    def test_manager_creates_salesperson_with_audit(self):
        linked_user = self.user("linked")
        self.manager_login()

        response = self.client.post(reverse("backoffice:salesperson_create"), {
            "user": linked_user.pk,
            "code": "S100",
            "name": "Vendedor Novo",
            "email": "novo@example.com",
            "active": "on",
        })

        salesperson = Salesperson.objects.get(code="S100")
        self.assertRedirects(response, reverse("backoffice:salesperson_detail", kwargs={"pk": salesperson.pk}))
        self.assertEqual(salesperson.user, linked_user)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CREATE, module="salespeople", object_id=str(salesperson.pk)).exists())

    def test_manager_updates_and_deactivates_salesperson_with_audit(self):
        self.manager_login()
        salesperson = Salesperson.objects.create(code="S101", name="Antes", active=True)

        self.client.post(reverse("backoffice:salesperson_update", kwargs={"pk": salesperson.pk}), {
            "code": "S101",
            "name": "Depois",
            "email": "depois@example.com",
        })

        salesperson.refresh_from_db()
        self.assertFalse(salesperson.active)
        log = AuditLog.objects.get(action=AuditLog.Action.DEACTIVATE, module="salespeople", object_id=str(salesperson.pk))
        self.assertEqual(log.before_data["active"], True)
        self.assertEqual(log.after_data["active"], False)

    def test_search_filter_and_customer_count(self):
        self.manager_login()
        salesperson = Salesperson.objects.create(code="S102", name="Ana Comercial", active=True)
        Customer.objects.create(legal_name="Cliente Ana", assigned_salesperson=salesperson)

        response = self.client.get(reverse("backoffice:salesperson_list"), {"q": "Ana", "active": "1"})

        self.assertContains(response, "Ana Comercial")
        self.assertContains(response, "1 cliente(s)")

    def test_viewer_is_read_only_and_manager_manages(self):
        salesperson = Salesperson.objects.create(code="S103", name="Leitura", active=True)
        viewer = self.user("viewer", role=BackofficeRole.VIEWER)
        self.client.force_login(viewer)

        self.assertEqual(self.client.get(reverse("backoffice:salesperson_detail", kwargs={"pk": salesperson.pk})).status_code, 200)
        self.assertEqual(self.client.get(reverse("backoffice:salesperson_create")).status_code, 403)

    def test_salesperson_role_does_not_manage_salespeople(self):
        user = self.user("seller", role=BackofficeRole.SALESPERSON)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:salesperson_list"))

        self.assertEqual(response.status_code, 403)
