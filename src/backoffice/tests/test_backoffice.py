from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from src.backoffice.models import AuditLog
from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.registry import BackofficeRole
from src.backoffice.permissions.registry import REAL_PERMISSION_MAP
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.commerce.models import Brand
from src.commerce.models import Category
from src.commerce.models import Product


class BackofficeBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_backoffice_rbac()
        cls.user_model = get_user_model()

    def create_user(self, username="panel-user", password="SenhaTeste123!Segura", role=None, **kwargs):
        user = self.user_model.objects.create_user(username=username, password=password, **kwargs)
        if role:
            user.groups.add(Group.objects.get(name=role.value))
        return user


class BackofficeRoleSyncCommandTests(BackofficeBaseTestCase):
    def test_command_creates_missing_groups(self):
        Group.objects.filter(name__in=[role.value for role in BackofficeRole]).delete()

        call_command("sync_backoffice_roles", verbosity=0)

        for role in BackofficeRole:
            with self.subTest(role=role):
                self.assertTrue(Group.objects.filter(name=role.value).exists())

    def test_command_is_idempotent(self):
        call_command("sync_backoffice_roles", verbosity=0)
        first_counts = {group.name: group.permissions.count() for group in Group.objects.filter(name__in=[role.value for role in BackofficeRole])}

        call_command("sync_backoffice_roles", verbosity=0)
        second_counts = {group.name: group.permissions.count() for group in Group.objects.filter(name__in=[role.value for role in BackofficeRole])}

        self.assertEqual(first_counts, second_counts)

    def test_real_permissions_are_associated_to_roles(self):
        call_command("sync_backoffice_roles", verbosity=0)
        viewer = Group.objects.get(name=BackofficeRole.VIEWER.value)
        permission_ref = REAL_PERMISSION_MAP[BackofficePermission.DASHBOARD_VIEW]

        self.assertTrue(
            viewer.permissions.filter(
                content_type__app_label=permission_ref.app_label,
                codename=permission_ref.codename,
            ).exists()
        )

    def test_reserved_permissions_are_not_created_as_fake_permissions(self):
        call_command("sync_backoffice_roles", verbosity=0)

        self.assertFalse(Permission.objects.filter(codename="customers_view").exists())
        self.assertFalse(Permission.objects.filter(codename="commerce_products_create").exists())

    def test_command_preserves_external_group_permissions(self):
        call_command("sync_backoffice_roles", verbosity=0)
        group = Group.objects.get(name=BackofficeRole.VIEWER.value)
        external_permission = Permission.objects.get(codename="add_user")
        group.permissions.add(external_permission)

        call_command("sync_backoffice_roles", verbosity=0)

        self.assertTrue(group.permissions.filter(pk=external_permission.pk).exists())


class BackofficeDashboardTests(BackofficeBaseTestCase):
    def test_anonymous_user_is_redirected_to_login_with_next(self):
        response = self.client.get(reverse("backoffice:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('institutional:login')}?next={reverse('backoffice:dashboard')}",
        )

    def test_authorized_user_accesses_dashboard(self):
        user = self.create_user(role=BackofficeRole.VIEWER)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/dashboard.html")
        self.assertContains(response, "Painel Administrativo")

    def test_user_without_permission_receives_403(self):
        user = self.create_user(username="blocked-user")
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "backoffice/403.html")

    def test_superuser_accesses_dashboard(self):
        user = self.create_user(username="root-user", is_superuser=True, is_staff=True)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:dashboard"))

        self.assertEqual(response.status_code, 200)

    def test_dashboard_uses_commerce_models_for_metrics(self):
        category = Category.objects.create(name="Robótica", slug="robotica")
        Brand.objects.create(name="Smart Control", slug="smart-control")
        Product.objects.create(name="Produto ativo", slug="produto-ativo", category=category, active=True)
        Product.objects.create(name="Produto inativo", slug="produto-inativo", category=category, active=False)
        user = self.create_user(role=BackofficeRole.VIEWER)
        self.client.force_login(user)

        response = self.client.get(reverse("backoffice:dashboard"))

        self.assertContains(response, "Produtos cadastrados")
        self.assertContains(response, "Produtos publicados")
        self.assertContains(response, "Categorias")
        self.assertContains(response, "Marcas")

    def test_login_with_next_can_return_to_panel(self):
        self.create_user(username="next-panel", role=BackofficeRole.VIEWER)

        response = self.client.post(
            f"{reverse('institutional:login')}?next={reverse('backoffice:dashboard')}",
            {
                "username": "next-panel",
                "password": "SenhaTeste123!Segura",
                "next": reverse("backoffice:dashboard"),
            },
        )

        self.assertRedirects(response, reverse("backoffice:dashboard"))

    def test_shop_still_responds(self):
        response = self.client.get(reverse("commerce:shop"))

        self.assertEqual(response.status_code, 200)


class BackofficeAuditTests(BackofficeBaseTestCase):
    def test_successful_login_generates_audit_log(self):
        self.create_user(username="login-ok")

        self.client.post(
            reverse("institutional:login"),
            {"username": "login-ok", "password": "SenhaTeste123!Segura"},
            HTTP_USER_AGENT="Test Browser",
            REMOTE_ADDR="127.0.0.1",
        )

        log = AuditLog.objects.get(action=AuditLog.Action.LOGIN_SUCCESS)
        self.assertEqual(log.module, "auth")
        self.assertEqual(log.actor.get_username(), "login-ok")
        self.assertEqual(log.ip_address, "127.0.0.1")
        self.assertEqual(log.user_agent, "Test Browser")
        self.assertNotIn("password", log.metadata)

    def test_invalid_login_generates_audit_log_without_credentials(self):
        self.client.post(
            reverse("institutional:login"),
            {"username": "missing-user", "password": "senha-incorreta"},
            HTTP_USER_AGENT="Test Browser",
            REMOTE_ADDR="127.0.0.1",
        )

        log = AuditLog.objects.get(action=AuditLog.Action.LOGIN_FAILED)
        self.assertIsNone(log.actor)
        self.assertEqual(log.metadata, {"username": "missing-user"})
        self.assertNotIn("password", log.metadata)

    def test_logout_generates_audit_log(self):
        user = self.create_user(username="logout-ok")
        self.client.force_login(user)

        self.client.post(reverse("institutional:logout"))

        log = AuditLog.objects.filter(action=AuditLog.Action.LOGOUT).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, user)

    def test_audit_log_accepts_json_fields(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            module="tests",
            before_data={"status": "draft"},
            after_data={"status": "published"},
            metadata={"source": "unit-test"},
        )

        self.assertEqual(log.before_data["status"], "draft")
        self.assertEqual(log.after_data["status"], "published")
        self.assertEqual(log.metadata["source"], "unit-test")

    def test_audit_log_cannot_be_changed_or_deleted_by_model_flow(self):
        log = AuditLog.objects.create(action=AuditLog.Action.CREATE, module="tests")

        log.module = "changed"
        with self.assertRaises(ValueError):
            log.save()

        with self.assertRaises(ValueError):
            log.delete()


class BackofficeHeaderLinkTests(BackofficeBaseTestCase):
    def test_anonymous_header_login_link_points_to_panel_next(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertContains(response, f"{reverse('institutional:login')}?next={reverse('backoffice:dashboard')}")
        self.assertContains(response, "Entrar")

    def test_authenticated_header_shows_panel_link(self):
        user = self.create_user(username="header-user", role=BackofficeRole.VIEWER)
        self.client.force_login(user)

        response = self.client.get(reverse("institutional:home"))

        self.assertContains(response, f"href=\"{reverse('backoffice:dashboard')}\"")
        self.assertContains(response, "Painel")

    def test_login_with_external_next_remains_blocked(self):
        self.create_user(username="safe-next-user")

        response = self.client.post(
            reverse("institutional:login"),
            {
                "username": "safe-next-user",
                "password": "SenhaTeste123!Segura",
                "next": "https://malicioso.example/painel/",
            },
        )

        self.assertRedirects(response, reverse("institutional:home"))
