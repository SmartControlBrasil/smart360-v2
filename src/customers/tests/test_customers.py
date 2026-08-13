from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from src.backoffice.models import AuditLog
from src.backoffice.permissions.registry import BackofficeRole
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.customers.models import Customer
from src.salespeople.models import Salesperson


class CustomerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_backoffice_rbac()
        cls.user_model = get_user_model()

    def user(self, username, role=None, **kwargs):
        user = self.user_model.objects.create_user(username=username, password="SenhaTeste123!Segura", **kwargs)
        if role:
            user.groups.add(Group.objects.get(name=role.value))
        return user

    def salesperson(self, name="Vendedor", user=None, code="V001"):
        return Salesperson.objects.create(user=user, code=code, name=name, email=f"{code.lower()}@example.com", active=True)

    def customer(self, name="Cliente", salesperson=None, document=None, status=Customer.Status.PROSPECT):
        return Customer.objects.create(legal_name=name, document=document, assigned_salesperson=salesperson, status=status)


class CustomerModelTests(CustomerTestCase):
    def test_customer_creation_and_optional_document(self):
        customer = self.customer(document=None)

        self.assertEqual(str(customer), "Cliente")
        self.assertIsNone(customer.document)

    def test_document_is_normalized(self):
        customer = self.customer(document="12.345.678/0001-90")

        self.assertEqual(customer.document, "12345678000190")

    def test_document_is_unique_when_present(self):
        self.customer(name="A", document="12345678901")

        with self.assertRaises(IntegrityError):
            self.customer(name="B", document="123.456.789-01")

    def test_assign_salesperson_and_created_updated_by(self):
        user = self.user("creator")
        salesperson = self.salesperson(user=user)
        customer = Customer.objects.create(legal_name="Empresa", assigned_salesperson=salesperson, created_by=user, updated_by=user)

        self.assertEqual(customer.assigned_salesperson, salesperson)
        self.assertEqual(customer.created_by, user)
        self.assertEqual(customer.updated_by, user)


class CustomerBackofficeTests(CustomerTestCase):
    def manager_login(self):
        user = self.user("manager", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.client.force_login(user)
        return user

    def test_manager_creates_customer_with_audit(self):
        user = self.manager_login()
        salesperson = self.salesperson(code="S100")

        response = self.client.post(reverse("backoffice:customer_create"), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "ACME Industrial",
            "document": "12.345.678/0001-90",
            "email": "acme@example.com",
            "assigned_salesperson": salesperson.pk,
            "status": Customer.Status.PROSPECT,
        })

        customer = Customer.objects.get(legal_name="ACME Industrial")
        self.assertRedirects(response, reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        self.assertEqual(customer.document, "12345678000190")
        self.assertEqual(customer.created_by, user)
        self.assertEqual(customer.updated_by, user)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CREATE, module="customers", object_id=str(customer.pk)).exists())

    def test_manager_updates_customer_with_before_after_audit(self):
        self.manager_login()
        customer = self.customer(name="Antes")

        response = self.client.post(reverse("backoffice:customer_update", kwargs={"pk": customer.pk}), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "Depois",
            "status": Customer.Status.ACTIVE,
        })

        customer.refresh_from_db()
        self.assertRedirects(response, reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        log = AuditLog.objects.get(action=AuditLog.Action.UPDATE, module="customers", object_id=str(customer.pk))
        self.assertEqual(log.before_data["legal_name"], "Antes")
        self.assertEqual(log.after_data["legal_name"], "Depois")

    def test_deactivate_and_activate_are_audited(self):
        self.manager_login()
        customer = self.customer(status=Customer.Status.ACTIVE)

        self.client.post(reverse("backoffice:customer_update", kwargs={"pk": customer.pk}), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": customer.legal_name,
            "status": Customer.Status.INACTIVE,
        })
        self.client.post(reverse("backoffice:customer_update", kwargs={"pk": customer.pk}), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": customer.legal_name,
            "status": Customer.Status.ACTIVE,
        })

        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.DEACTIVATE, object_id=str(customer.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.ACTIVATE, object_id=str(customer.pk)).exists())

    def test_search_and_filters(self):
        user = self.manager_login()
        salesperson = self.salesperson(user=user)
        self.customer(name="Robótica Alfa", salesperson=salesperson, document="11122233344", status=Customer.Status.ACTIVE)
        self.customer(name="Empresa Beta", status=Customer.Status.INACTIVE)

        response = self.client.get(reverse("backoffice:customer_list"), {"q": "Alfa", "status": Customer.Status.ACTIVE, "salesperson": salesperson.pk})

        self.assertContains(response, "Robótica Alfa")
        self.assertNotContains(response, "Empresa Beta")

    def test_salesperson_sees_own_customer_and_not_other_customer(self):
        user = self.user("seller", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="Seller", user=user, code="S200")
        other = self.salesperson(name="Other", code="S201")
        own = self.customer(name="Cliente Próprio", salesperson=seller)
        alien = self.customer(name="Cliente Alheio", salesperson=other)
        self.client.force_login(user)

        list_response = self.client.get(reverse("backoffice:customer_list"))
        detail_response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": own.pk}))
        idor_response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": alien.pk}))

        self.assertContains(list_response, "Cliente Próprio")
        self.assertNotContains(list_response, "Cliente Alheio")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(idor_response.status_code, 404)


    def test_salesperson_can_create_and_edit_own_customer(self):
        user = self.user("seller-create", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="Seller", user=user, code="S300")
        self.client.force_login(user)

        create_response = self.client.post(reverse("backoffice:customer_create"), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "Cliente Novo",
            "status": Customer.Status.PROSPECT,
        })
        customer = Customer.objects.get(legal_name="Cliente Novo")
        edit_response = self.client.post(reverse("backoffice:customer_update", kwargs={"pk": customer.pk}), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "Cliente Próprio Editado",
            "status": Customer.Status.ACTIVE,
        })

        self.assertRedirects(create_response, reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        self.assertEqual(customer.assigned_salesperson, seller)
        self.assertRedirects(edit_response, reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        customer.refresh_from_db()
        self.assertEqual(customer.legal_name, "Cliente Próprio Editado")
        self.assertEqual(customer.assigned_salesperson, seller)

    def test_salesperson_cannot_edit_other_salesperson_customer_by_post(self):
        user = self.user("seller-post", role=BackofficeRole.SALESPERSON)
        self.salesperson(name="Seller", user=user, code="S301")
        other = self.salesperson(name="Other", code="S302")
        alien = self.customer(name="Cliente Alheio POST", salesperson=other)
        self.client.force_login(user)

        response = self.client.post(reverse("backoffice:customer_update", kwargs={"pk": alien.pk}), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "Tentativa Indevida",
            "status": Customer.Status.ACTIVE,
        })

        self.assertEqual(response.status_code, 404)
        alien.refresh_from_db()
        self.assertEqual(alien.legal_name, "Cliente Alheio POST")

    def test_catalog_manager_cannot_access_customers(self):
        user = self.user("catalog", role=BackofficeRole.CATALOG_MANAGER)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_list"))

        self.assertEqual(response.status_code, 403)

    def test_viewer_is_read_only(self):
        user = self.user("viewer", role=BackofficeRole.VIEWER)
        self.client.force_login(user)
        customer = self.customer()

        self.assertEqual(self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk})).status_code, 200)
        self.assertEqual(self.client.get(reverse("backoffice:customer_create")).status_code, 403)
