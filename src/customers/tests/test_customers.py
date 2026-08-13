from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import importlib

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase
from unittest import mock
from django.urls import reverse

from src.backoffice.models import AccessScope
from src.backoffice.models import AuditLog
from src.backoffice.models import BusinessUnit
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.models import Department
from src.backoffice.models import Team
from src.backoffice.models import DEFAULT_BUSINESS_UNIT_CODE
from src.backoffice.models import DEFAULT_BUSINESS_UNIT_NAME
from src.backoffice.models import DEFAULT_BUSINESS_UNIT_SLUG
from src.backoffice.permissions.registry import BackofficeRole
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.customers.models import Customer
from src.customers.models import CustomerAssignmentTransfer
from src.customers.models import CustomerBusinessRelationship
from src.customers.services import transfer_customer_relationship
from src.customers.services import valid_salespeople_for_relationship
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

    def business_unit(self, code=DEFAULT_BUSINESS_UNIT_CODE, name=DEFAULT_BUSINESS_UNIT_NAME, slug=DEFAULT_BUSINESS_UNIT_SLUG):
        return BusinessUnit.objects.get_or_create(code=code, defaults={"name": name, "slug": slug})[0]

    def membership(self, user, business_unit=None, scope=AccessScope.ALL, is_active=True, department=None, team=None):
        return BusinessUnitMembership.objects.create(
            user=user,
            business_unit=business_unit or self.business_unit(),
            department=department,
            team=team,
            scope=scope,
            is_active=is_active,
        )

    def department(self, business_unit=None, name="Comercial", code="COM", slug="comercial", is_active=True):
        return Department.objects.create(
            business_unit=business_unit or self.business_unit(),
            name=name,
            code=code,
            slug=slug,
            is_active=is_active,
        )

    def team(self, department=None, name="Equipe Robótica", code="ROB", slug="robotica", is_active=True):
        return Team.objects.create(
            department=department or self.department(),
            name=name,
            code=code,
            slug=slug,
            is_active=is_active,
        )

    def salesperson(self, name="Vendedor", user=None, code="V001"):
        return Salesperson.objects.create(user=user, code=code, name=name, email=f"{code.lower()}@example.com", active=True)

    def customer(self, name="Cliente", salesperson=None, document=None, status=Customer.Status.PROSPECT, business_unit=None):
        customer = Customer.objects.create(legal_name=name, document=document, assigned_salesperson=salesperson, status=status)
        CustomerBusinessRelationship.objects.create(
            customer=customer,
            business_unit=business_unit or self.business_unit(),
            assigned_salesperson=salesperson,
            status=status,
        )
        return customer


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
            with transaction.atomic():
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
        self.membership(user, scope=AccessScope.OWN)
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
        self.membership(user, scope=AccessScope.OWN)
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
        self.membership(user, scope=AccessScope.OWN)
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

class MultiunitFoundationTests(CustomerTestCase):
    def test_business_unit_creation_uniqueness_and_activation(self):
        unit = self.business_unit(code="MC_CLIMA", name="MC Clima", slug="mc-clima")

        self.assertEqual(str(unit), "MC Clima")
        unit.is_active = False
        unit.save(update_fields=["is_active", "updated_at"])
        unit.refresh_from_db()
        self.assertFalse(unit.is_active)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BusinessUnit.objects.create(code="MC_CLIMA", name="Duplicada", slug="outra")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BusinessUnit.objects.create(code="OUTRA", name="Outra", slug="mc-clima")

    def test_user_can_have_multiple_business_unit_memberships_and_inactive_does_not_grant_access(self):
        user = self.user("multi-seller", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="Multi", user=user, code="M001")
        robotics = self.business_unit()
        clima = self.business_unit(code="MC_CLIMA", name="MC Clima", slug="mc-clima")
        self.membership(user, robotics, scope=AccessScope.OWN)
        self.membership(user, clima, scope=AccessScope.OWN, is_active=False)
        visible = self.customer(name="Robótica", salesperson=seller, business_unit=robotics)
        hidden = self.customer(name="Cliente Unidade Inativa", salesperson=seller, business_unit=clima)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_list"))

        self.assertContains(response, visible.legal_name)
        self.assertNotContains(response, hidden.legal_name)

    def test_scope_choices_validate_supported_values(self):
        choices = {value for value, _label in AccessScope.choices}

        self.assertEqual(choices, {"ALL", "DEPARTMENT", "TEAM", "OWN", "NONE"})

    def test_customer_can_have_relationships_with_multiple_units_and_different_salespeople(self):
        customer = self.customer(name="Empresa Multi")
        clima = self.business_unit(code="MC_CLIMA", name="MC Clima", slug="mc-clima")
        sites = self.business_unit(code="MC_SITES", name="MC Sites", slug="mc-sites")
        joao = self.salesperson(name="João", code="J001")
        fagner = self.salesperson(name="Fagner", code="F001")
        CustomerBusinessRelationship.objects.create(customer=customer, business_unit=clima, assigned_salesperson=joao)
        CustomerBusinessRelationship.objects.create(customer=customer, business_unit=sites, assigned_salesperson=fagner)

        self.assertEqual(customer.business_relationships.count(), 3)
        self.assertEqual(customer.business_relationships.get(business_unit=clima).assigned_salesperson, joao)
        self.assertEqual(customer.business_relationships.get(business_unit=sites).assigned_salesperson, fagner)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CustomerBusinessRelationship.objects.create(customer=customer, business_unit=clima)

    def test_data_migration_creates_default_relationships_and_preserves_salesperson(self):
        customer = Customer.objects.create(legal_name="Legado", assigned_salesperson=self.salesperson(code="LEG001"))
        CustomerBusinessRelationship.objects.filter(customer=customer).delete()
        migration = importlib.import_module("src.customers.migrations.0002_customerbusinessrelationship")

        migration.create_default_customer_relationships(importlib.import_module("django.apps").apps, None)
        migration.create_default_customer_relationships(importlib.import_module("django.apps").apps, None)

        relationships = CustomerBusinessRelationship.objects.filter(customer=customer, business_unit__code=DEFAULT_BUSINESS_UNIT_CODE)
        self.assertEqual(relationships.count(), 1)
        self.assertEqual(relationships.get().assigned_salesperson, customer.assigned_salesperson)

    def test_system_admin_sees_all_customers(self):
        user = self.user("system-admin", role=BackofficeRole.SYSTEM_ADMIN)
        self.customer(name="Cliente A")
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_list"))

        self.assertContains(response, "Cliente A")

    def test_salesperson_without_membership_does_not_gain_customer_access(self):
        user = self.user("seller-no-membership", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="Sem Membership", user=user, code="SM001")
        self.customer(name="Cliente Sem Membership", salesperson=seller)
        self.client.force_login(user)

        list_response = self.client.get(reverse("backoffice:customer_list"))
        create_response = self.client.post(reverse("backoffice:customer_create"), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "Cliente Criado Sem Membership",
            "status": Customer.Status.PROSPECT,
        })

        self.assertNotContains(list_response, "Cliente Sem Membership")
        self.assertEqual(create_response.status_code, 403)
        self.assertFalse(Customer.objects.filter(legal_name="Cliente Criado Sem Membership").exists())

    def test_membership_in_unit_a_does_not_grant_access_to_unit_b_get_or_post(self):
        user = self.user("seller-unit-a", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="Unidade A", user=user, code="UA001")
        unit_a = self.business_unit(code="UNIT_A", name="Unidade A", slug="unit-a")
        unit_b = self.business_unit(code="UNIT_B", name="Unidade B", slug="unit-b")
        self.membership(user, unit_a, scope=AccessScope.OWN)
        visible = self.customer(name="Cliente Unidade A", salesperson=seller, business_unit=unit_a)
        hidden = self.customer(name="Cliente Unidade B", salesperson=seller, business_unit=unit_b)
        self.client.force_login(user)

        list_response = self.client.get(reverse("backoffice:customer_list"))
        detail_response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": hidden.pk}))
        post_response = self.client.post(reverse("backoffice:customer_update", kwargs={"pk": hidden.pk}), {
            "customer_type": Customer.CustomerType.COMPANY,
            "legal_name": "Tentativa Unidade B",
            "status": Customer.Status.ACTIVE,
        })

        self.assertContains(list_response, visible.legal_name)
        self.assertNotContains(list_response, hidden.legal_name)
        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        hidden.refresh_from_db()
        self.assertEqual(hidden.legal_name, "Cliente Unidade B")


class CustomerBusinessRelationshipUITests(CustomerTestCase):
    def test_customer_detail_shows_default_relationship(self):
        user = self.user("relationship-manager", role=BackofficeRole.COMMERCIAL_MANAGER)
        customer = self.customer(name="Empresa Relacionada")
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relacionamentos comerciais")
        self.assertContains(response, "Smart Control Brasil")

    def test_customer_detail_with_multiple_relationships_shows_all_permitted_to_admin(self):
        user = self.user("relationship-admin", role=BackofficeRole.SYSTEM_ADMIN)
        customer = self.customer(name="Empresa Multi UI")
        clima = self.business_unit(code="UI_CLIMA", name="UI Clima", slug="ui-clima")
        sites = self.business_unit(code="UI_SITES", name="UI Sites", slug="ui-sites")
        CustomerBusinessRelationship.objects.create(customer=customer, business_unit=clima, status=Customer.Status.ACTIVE)
        CustomerBusinessRelationship.objects.create(customer=customer, business_unit=sites, status=Customer.Status.PROSPECT)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))

        self.assertContains(response, "Smart Control Brasil")
        self.assertContains(response, "UI Clima")
        self.assertContains(response, "UI Sites")

    def test_salesperson_does_not_see_relationship_from_forbidden_unit(self):
        user = self.user("relationship-seller", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="Seller UI", user=user, code="RSELL")
        allowed_unit = self.business_unit(code="REL_A", name="Relacionamento A", slug="rel-a")
        forbidden_unit = self.business_unit(code="REL_B", name="Relacionamento B", slug="rel-b")
        self.membership(user, allowed_unit, scope=AccessScope.OWN)
        customer = self.customer(name="Cliente Parcial", salesperson=seller, business_unit=allowed_unit)
        CustomerBusinessRelationship.objects.create(
            customer=customer,
            business_unit=forbidden_unit,
            assigned_salesperson=seller,
            status=Customer.Status.ACTIVE,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relacionamento A")
        self.assertNotContains(response, "Relacionamento B")

    def test_customer_list_business_unit_filter_is_available_when_multiple_units_exist(self):
        user = self.user("relationship-filter-admin", role=BackofficeRole.SYSTEM_ADMIN)
        unit_a = self.business_unit(code="FILTER_A", name="Filtro A", slug="filter-a")
        unit_b = self.business_unit(code="FILTER_B", name="Filtro B", slug="filter-b")
        visible = self.customer(name="Cliente Filtro A", business_unit=unit_a)
        hidden = self.customer(name="Cliente Filtro B", business_unit=unit_b)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_list"), {"business_unit": unit_a.pk})

        self.assertContains(response, "customer-business-unit")
        self.assertContains(response, visible.legal_name)
        self.assertNotContains(response, hidden.legal_name)

    def test_salesperson_direct_id_does_not_expose_customer_from_forbidden_unit(self):
        user = self.user("relationship-idor-seller", role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name="IDOR Seller", user=user, code="IDOR1")
        unit_a = self.business_unit(code="IDOR_A", name="IDOR A", slug="idor-a")
        unit_b = self.business_unit(code="IDOR_B", name="IDOR B", slug="idor-b")
        self.membership(user, unit_a, scope=AccessScope.OWN)
        forbidden = self.customer(name="Cliente IDOR B", salesperson=seller, business_unit=unit_b)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": forbidden.pk}))

        self.assertEqual(response.status_code, 404)


class OrganizationalScopeTests(CustomerTestCase):
    def org_fixture(self):
        unit_a = self.business_unit(code="SCOPE_A", name="Scope A", slug="scope-a")
        unit_b = self.business_unit(code="SCOPE_B", name="Scope B", slug="scope-b")
        comercial = self.department(unit_a, name="Comercial", code="COM", slug="com")
        outro = self.department(unit_a, name="Outro", code="OUT", slug="out")
        comercial_b = self.department(unit_b, name="Comercial B", code="COMB", slug="comb")
        robotica = self.team(comercial, name="Equipe Robótica", code="ROB", slug="rob")
        automacao = self.team(comercial, name="Equipe Automação", code="AUT", slug="aut")
        outro_team = self.team(outro, name="Equipe Outro", code="OUTT", slug="outt")
        team_b = self.team(comercial_b, name="Equipe B", code="B", slug="b")
        return unit_a, unit_b, comercial, outro, comercial_b, robotica, automacao, outro_team, team_b

    def seller_with_membership(self, username, unit, department, team, code):
        user = self.user(username, role=BackofficeRole.SALESPERSON)
        seller = self.salesperson(name=username, user=user, code=code)
        self.membership(user, unit, scope=AccessScope.OWN, department=department, team=team)
        return user, seller

    def test_department_and_team_models_and_membership_validation(self):
        unit = self.business_unit(code="MODEL_UNIT", name="Model Unit", slug="model-unit")
        other_unit = self.business_unit(code="MODEL_OTHER", name="Model Other", slug="model-other")
        department = self.department(unit, code="COM", slug="com")
        other_department = self.department(other_unit, code="COM", slug="com")
        team = self.team(department, code="ROB", slug="rob")
        other_team = self.team(other_department, code="ROB", slug="rob")

        self.assertEqual(team.department.business_unit, unit)
        department.is_active = False
        department.save(update_fields=["is_active", "updated_at"])
        department.refresh_from_db()
        self.assertFalse(department.is_active)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Department.objects.create(business_unit=unit, name="Duplicado", code="COM", slug="novo")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Team.objects.create(department=department, name="Duplicada", code="ROB", slug="nova")

        user = self.user("validation-user")
        valid_department = BusinessUnitMembership(user=user, business_unit=unit, department=department, scope=AccessScope.DEPARTMENT)
        valid_department.full_clean()
        with self.assertRaises(ValidationError):
            BusinessUnitMembership(user=user, business_unit=unit, scope=AccessScope.DEPARTMENT).full_clean()
        with self.assertRaises(ValidationError):
            BusinessUnitMembership(user=user, business_unit=unit, department=other_department, scope=AccessScope.DEPARTMENT).full_clean()
        with self.assertRaises(ValidationError):
            BusinessUnitMembership(user=user, business_unit=unit, department=department, team=other_team, scope=AccessScope.TEAM).full_clean()
        valid_team = BusinessUnitMembership(user=user, business_unit=unit, department=department, team=team, scope=AccessScope.TEAM)
        valid_team.full_clean()
        for scope in [AccessScope.ALL, AccessScope.OWN, AccessScope.NONE]:
            BusinessUnitMembership(user=user, business_unit=unit, scope=scope).full_clean()

    def test_all_department_team_own_none_scopes(self):
        unit_a, unit_b, comercial, outro, _comercial_b, robotica, automacao, outro_team, team_b = self.org_fixture()
        robot_user, robot_seller = self.seller_with_membership("robot-seller", unit_a, comercial, robotica, "ROBSELL")
        auto_user, auto_seller = self.seller_with_membership("auto-seller", unit_a, comercial, automacao, "AUTSELL")
        outro_user, outro_seller = self.seller_with_membership("outro-seller", unit_a, outro, outro_team, "OUTSELL")
        b_user, b_seller = self.seller_with_membership("b-seller", unit_b, team_b.department, team_b, "BSELL")
        robot_customer = self.customer("Cliente Robótica", robot_seller, business_unit=unit_a)
        auto_customer = self.customer("Cliente Automação", auto_seller, business_unit=unit_a)
        outro_customer = self.customer("Cliente Outro", outro_seller, business_unit=unit_a)
        b_customer = self.customer("Cliente B", b_seller, business_unit=unit_b)

        all_user = self.user("all-a", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.membership(all_user, unit_a, scope=AccessScope.ALL)
        dept_user = self.user("dept-a", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.membership(dept_user, unit_a, scope=AccessScope.DEPARTMENT, department=comercial)
        team_user = self.user("team-robot", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.membership(team_user, unit_a, scope=AccessScope.TEAM, department=comercial, team=robotica)
        own_user = self.user("own-robot", role=BackofficeRole.SALESPERSON)
        own_seller = self.salesperson(name="Own Robot", user=own_user, code="OWNROB")
        self.membership(own_user, unit_a, scope=AccessScope.OWN, department=comercial, team=robotica)
        own_customer = self.customer("Cliente Próprio Scope", own_seller, business_unit=unit_a)
        none_user = self.user("none-a", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.membership(none_user, unit_a, scope=AccessScope.NONE)

        cases = [
            (all_user, [robot_customer, auto_customer, outro_customer], [b_customer]),
            (dept_user, [robot_customer, auto_customer], [outro_customer, b_customer]),
            (team_user, [robot_customer], [auto_customer, outro_customer, b_customer]),
            (own_user, [own_customer], [robot_customer, auto_customer, outro_customer, b_customer]),
            (none_user, [], [robot_customer, auto_customer, outro_customer, b_customer]),
        ]
        for user, visible, hidden in cases:
            self.client.force_login(user)
            response = self.client.get(reverse("backoffice:customer_list"))
            for customer in visible:
                self.assertContains(response, customer.legal_name)
            for customer in hidden:
                self.assertNotContains(response, customer.legal_name)

    def test_customers_without_salesperson_only_visible_to_all(self):
        unit = self.business_unit(code="NULL_UNIT", name="Null Unit", slug="null-unit")
        department = self.department(unit, code="NULLD", slug="nulld")
        team = self.team(department, code="NULLT", slug="nullt")
        customer = self.customer("Cliente Sem Responsável", salesperson=None, business_unit=unit)
        users = []
        for scope in [AccessScope.ALL, AccessScope.DEPARTMENT, AccessScope.TEAM, AccessScope.OWN, AccessScope.NONE]:
            user = self.user(f"null-{scope.lower()}", role=BackofficeRole.COMMERCIAL_MANAGER if scope != AccessScope.OWN else BackofficeRole.SALESPERSON)
            self.membership(user, unit, scope=scope, department=department if scope in [AccessScope.DEPARTMENT, AccessScope.TEAM] else None, team=team if scope == AccessScope.TEAM else None)
            users.append((scope, user))

        for scope, user in users:
            self.client.force_login(user)
            response = self.client.get(reverse("backoffice:customer_list"))
            if scope == AccessScope.ALL:
                self.assertContains(response, customer.legal_name)
            else:
                self.assertNotContains(response, customer.legal_name)

    def test_department_team_and_business_unit_idor_are_blocked(self):
        unit_a, unit_b, comercial, outro, _comercial_b, robotica, automacao, outro_team, team_b = self.org_fixture()
        _robot_user, robot_seller = self.seller_with_membership("idor-robot-seller", unit_a, comercial, robotica, "IDROB")
        _auto_user, auto_seller = self.seller_with_membership("idor-auto-seller", unit_a, comercial, automacao, "IDAUT")
        _outro_user, outro_seller = self.seller_with_membership("idor-outro-seller", unit_a, outro, outro_team, "IDOUT")
        _b_user, b_seller = self.seller_with_membership("idor-b-seller", unit_b, team_b.department, team_b, "IDB")
        robot_customer = self.customer("IDOR Robótica", robot_seller, business_unit=unit_a)
        auto_customer = self.customer("IDOR Automação", auto_seller, business_unit=unit_a)
        outro_customer = self.customer("IDOR Outro", outro_seller, business_unit=unit_a)
        b_customer = self.customer("IDOR B", b_seller, business_unit=unit_b)

        team_user = self.user("idor-team-user", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.membership(team_user, unit_a, scope=AccessScope.TEAM, department=comercial, team=robotica)
        dept_user = self.user("idor-dept-user", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.membership(dept_user, unit_a, scope=AccessScope.DEPARTMENT, department=comercial)

        self.client.force_login(team_user)
        self.assertEqual(self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": auto_customer.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": b_customer.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": robot_customer.pk})).status_code, 200)
        self.client.force_login(dept_user)
        self.assertEqual(self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": outro_customer.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse("backoffice:customer_update", kwargs={"pk": b_customer.pk}), {"customer_type": Customer.CustomerType.COMPANY, "legal_name": "Hack", "status": Customer.Status.ACTIVE}).status_code, 404)


class CustomerAssignmentTransferTests(CustomerTestCase):
    def transfer_context(self):
        unit = self.business_unit(code="TRANSFER_A", name="Transfer A", slug="transfer-a")
        department = self.department(unit, code="TRD", slug="trd")
        team = self.team(department, code="TRT", slug="trt")
        old_user = self.user("transfer-old", role=BackofficeRole.SALESPERSON)
        new_user = self.user("transfer-new", role=BackofficeRole.SALESPERSON)
        actor = self.user("transfer-manager", role=BackofficeRole.COMMERCIAL_MANAGER)
        old_seller = self.salesperson("Transfer Old", old_user, "TOLD")
        new_seller = self.salesperson("Transfer New", new_user, "TNEW")
        self.membership(old_user, unit, scope=AccessScope.OWN, department=department, team=team)
        self.membership(new_user, unit, scope=AccessScope.OWN, department=department, team=team)
        self.membership(actor, unit, scope=AccessScope.DEPARTMENT, department=department)
        customer = self.customer("Cliente Transfer", old_seller, business_unit=unit)
        relationship = customer.business_relationships.get(business_unit=unit)
        return unit, department, team, actor, old_seller, new_seller, customer, relationship

    def test_transfer_history_model_records_required_fields_and_is_append_only(self):
        _unit, _department, _team, actor, old_seller, new_seller, _customer, relationship = self.transfer_context()

        transfer = CustomerAssignmentTransfer.objects.create(
            relationship=relationship,
            previous_salesperson=old_seller,
            new_salesperson=new_seller,
            transferred_by=actor,
            reason="Redistribuição de carteira",
        )

        self.assertEqual(transfer.previous_salesperson, old_seller)
        self.assertEqual(transfer.new_salesperson, new_seller)
        self.assertEqual(transfer.transferred_by, actor)
        self.assertEqual(transfer.reason, "Redistribuição de carteira")
        self.assertIsNotNone(transfer.transferred_at)
        transfer.reason = "Alterar"
        with self.assertRaises(ValueError):
            transfer.save()
        with self.assertRaises(ValueError):
            transfer.delete()

    def test_valid_transfer_changes_relationship_creates_history_audit_and_preserves_created_by(self):
        unit, _department, _team, actor, old_seller, new_seller, customer, relationship = self.transfer_context()
        creator = self.user("creator-transfer")
        customer.created_by = creator
        customer.save(update_fields=["created_by"])
        relationship.created_by = creator
        relationship.save(update_fields=["created_by"])

        transfer = transfer_customer_relationship(
            relationship=relationship,
            new_salesperson=new_seller,
            actor=actor,
            reason="Redistribuição de carteira",
        )

        relationship.refresh_from_db()
        customer.refresh_from_db()
        self.assertEqual(relationship.assigned_salesperson, new_seller)
        self.assertEqual(CustomerAssignmentTransfer.objects.get(pk=transfer.pk).previous_salesperson, old_seller)
        self.assertTrue(AuditLog.objects.filter(module="customers.assignment_transfers", object_id=str(transfer.pk)).exists())
        self.assertEqual(customer.created_by, creator)
        self.assertEqual(relationship.created_by, creator)
        if unit.code == DEFAULT_BUSINESS_UNIT_CODE:
            self.assertEqual(customer.assigned_salesperson, new_seller)

    def test_transfer_rejects_same_seller_cross_unit_invalid_empty_reason_and_unpermitted_actor(self):
        unit, _department, _team, actor, old_seller, new_seller, _customer, relationship = self.transfer_context()
        other_unit = self.business_unit(code="TRANSFER_B", name="Transfer B", slug="transfer-b")
        other_user = self.user("other-transfer-user", role=BackofficeRole.SALESPERSON)
        other_seller = self.salesperson("Other Transfer", other_user, "TOTHER")
        self.membership(other_user, other_unit, scope=AccessScope.OWN)
        no_user_seller = self.salesperson("Sem User", None, "NOUSER")
        seller_actor = self.user("seller-cannot-transfer", role=BackofficeRole.SALESPERSON)
        self.membership(seller_actor, unit, scope=AccessScope.OWN)

        with self.assertRaises(ValidationError):
            transfer_customer_relationship(relationship=relationship, new_salesperson=old_seller, actor=actor, reason="Mesmo vendedor")
        with self.assertRaises(ValidationError):
            transfer_customer_relationship(relationship=relationship, new_salesperson=other_seller, actor=actor, reason="Outra unidade")
        with self.assertRaises(ValidationError):
            transfer_customer_relationship(relationship=relationship, new_salesperson=no_user_seller, actor=actor, reason="Sem user")
        with self.assertRaises(ValidationError):
            transfer_customer_relationship(relationship=relationship, new_salesperson=new_seller, actor=actor, reason="   ")
        with self.assertRaises(Exception):
            transfer_customer_relationship(relationship=relationship, new_salesperson=new_seller, actor=seller_actor, reason="Sem permissão")

    def test_transfer_only_changes_target_business_unit_relationship(self):
        _unit, _department, _team, actor, _old_seller, new_seller, customer, relationship = self.transfer_context()
        unit_b = self.business_unit(code="TRANSFER_MULTI_B", name="Transfer Multi B", slug="transfer-multi-b")
        b_user = self.user("transfer-b-user", role=BackofficeRole.SALESPERSON)
        b_seller = self.salesperson("Seller B", b_user, "TB")
        self.membership(b_user, unit_b, scope=AccessScope.OWN)
        rel_b = CustomerBusinessRelationship.objects.create(customer=customer, business_unit=unit_b, assigned_salesperson=b_seller)

        transfer_customer_relationship(relationship=relationship, new_salesperson=new_seller, actor=actor, reason="Somente unidade A")

        relationship.refresh_from_db()
        rel_b.refresh_from_db()
        self.assertEqual(relationship.assigned_salesperson, new_seller)
        self.assertEqual(rel_b.assigned_salesperson, b_seller)

    def test_department_manager_transfers_inside_department_and_cannot_transfer_other_department(self):
        unit, department, _team, actor, _old_seller, new_seller, _customer, relationship = self.transfer_context()
        other_department = self.department(unit, name="Financeiro", code="FIN", slug="fin")
        other_team = self.team(other_department, name="Financeiro", code="FINT", slug="fint")
        other_user = self.user("other-dept-seller", role=BackofficeRole.SALESPERSON)
        other_seller = self.salesperson("Other Dept", other_user, "ODEPT")
        self.membership(other_user, unit, scope=AccessScope.OWN, department=other_department, team=other_team)
        other_customer = self.customer("Cliente Outro Dept Transfer", other_seller, business_unit=unit)
        other_relationship = other_customer.business_relationships.get(business_unit=unit)

        transfer_customer_relationship(relationship=relationship, new_salesperson=new_seller, actor=actor, reason="Dentro do dept")
        with self.assertRaises(Exception):
            transfer_customer_relationship(relationship=other_relationship, new_salesperson=new_seller, actor=actor, reason="Fora do dept")

    def test_transfer_rolls_back_if_history_creation_fails(self):
        _unit, _department, _team, actor, old_seller, new_seller, _customer, relationship = self.transfer_context()

        with mock.patch("src.customers.models.CustomerAssignmentTransfer.save", side_effect=RuntimeError("history failed")):
            with self.assertRaises(RuntimeError):
                transfer_customer_relationship(relationship=relationship, new_salesperson=new_seller, actor=actor, reason="Falha controlada")

        relationship.refresh_from_db()
        self.assertEqual(relationship.assigned_salesperson, old_seller)

    def test_transfer_ui_button_form_filter_history_and_direct_block(self):
        unit, _department, _team, actor, old_seller, new_seller, customer, relationship = self.transfer_context()
        other_unit = self.business_unit(code="UI_OTHER", name="UI Other", slug="ui-other")
        other_user = self.user("ui-other-user", role=BackofficeRole.SALESPERSON)
        other_seller = self.salesperson("UI Other", other_user, "UIOTHER")
        self.membership(other_user, other_unit, scope=AccessScope.OWN)
        read_only_actor = self.user("ui-read-only-actor", role=BackofficeRole.VIEWER)

        self.client.force_login(actor)
        detail = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        form_response = self.client.get(reverse("backoffice:customer_relationship_transfer", kwargs={"pk": customer.pk, "relationship_pk": relationship.pk}))
        post_response = self.client.post(reverse("backoffice:customer_relationship_transfer", kwargs={"pk": customer.pk, "relationship_pk": relationship.pk}), {
            "new_salesperson": new_seller.pk,
            "reason": "Transferência via UI",
        })
        history_response = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        self.client.force_login(read_only_actor)
        blocked_detail = self.client.get(reverse("backoffice:customer_detail", kwargs={"pk": customer.pk}))
        blocked_post = self.client.post(reverse("backoffice:customer_relationship_transfer", kwargs={"pk": customer.pk, "relationship_pk": relationship.pk}), {
            "new_salesperson": old_seller.pk,
            "reason": "Bloqueado",
        })

        self.assertContains(detail, "Transferir responsável")
        self.assertContains(form_response, new_seller.name)
        self.assertNotContains(form_response, other_seller.name)
        self.assertEqual(post_response.status_code, 302)
        self.assertContains(history_response, "Histórico de responsáveis")
        self.assertContains(history_response, "Transferência via UI")
        self.assertNotContains(blocked_detail, "Transferir responsável")
        self.assertEqual(blocked_post.status_code, 403)
        self.assertIn(new_seller, valid_salespeople_for_relationship(relationship))
        self.assertNotIn(other_seller, valid_salespeople_for_relationship(relationship))
