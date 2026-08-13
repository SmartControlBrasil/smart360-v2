from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from src.backoffice.models import AuditLog
from src.backoffice.models import AccessScope
from src.backoffice.models import BusinessUnit
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.models import Department
from src.backoffice.models import Team
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


    def test_salesperson_role_receives_customer_write_permissions(self):
        self.create_user(username="seller-write-role", role=BackofficeRole.SALESPERSON)
        group = Group.objects.get(name=BackofficeRole.SALESPERSON.value)

        self.assertTrue(group.permissions.filter(content_type__app_label="customers", codename="add_customer").exists())
        self.assertTrue(group.permissions.filter(content_type__app_label="customers", codename="change_customer").exists())

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
        self.assertTrue(log.session_key)
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

from decimal import Decimal
from io import BytesIO
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from src.commerce.models import ProductImage

CATALOG_TEST_MEDIA_ROOT = tempfile.mkdtemp()


def catalog_image(name="image.jpg", image_format="JPEG", content_type="image/jpeg"):
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def catalog_product_payload(category, brand=None, **overrides):
    data = {
        "name": "Produto Painel",
        "slug": "produto-painel",
        "sku": "PAINEL-001",
        "category": category.pk,
        "brand": brand.pk if brand else "",
        "sale_mode": Product.SaleMode.QUOTE,
        "availability": Product.Availability.CHECK_AVAILABILITY,
        "short_description": "Resumo comercial",
        "description": "Descrição completa",
        "active": "on",
        "seo_title": "SEO Produto",
        "seo_description": "Descrição SEO",
    }
    data.update(overrides)
    return data


@override_settings(MEDIA_ROOT=CATALOG_TEST_MEDIA_ROOT)
class BackofficeCatalogTests(BackofficeBaseTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CATALOG_TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.category = Category.objects.create(name="Robótica", slug="robotica")
        self.brand = Brand.objects.create(name="Smart Brand", slug="smart-brand")

    def login_role(self, role):
        user = self.create_user(username=f"user-{role.value.lower()}", role=role)
        self.client.force_login(user)
        return user

    def product(self, **kwargs):
        data = {
            "name": "Produto Base",
            "slug": "produto-base",
            "sku": "BASE-001",
            "category": self.category,
            "brand": self.brand,
            "sale_mode": Product.SaleMode.QUOTE,
            "active": True,
        }
        data.update(kwargs)
        return Product.objects.create(**data)

    def test_catalog_manager_creates_product_and_shop_reflects_same_record(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)

        response = self.client.post(
            reverse("backoffice:product_create"),
            catalog_product_payload(self.category, self.brand),
        )

        product = Product.objects.get(slug="produto-painel")
        self.assertRedirects(response, reverse("backoffice:product_detail", kwargs={"pk": product.pk}))
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CREATE, module="commerce.products", object_id=str(product.pk)).exists())
        shop_response = self.client.get(reverse("commerce:shop"))
        self.assertContains(shop_response, "Produto Painel")

    def test_product_update_audits_before_after_and_validates_price(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)
        product = self.product()

        response = self.client.post(
            reverse("backoffice:product_update", kwargs={"pk": product.pk}),
            catalog_product_payload(
                self.category,
                self.brand,
                name="Produto Alterado",
                slug=product.slug,
                sku=product.sku,
                sale_mode=Product.SaleMode.DIRECT_AND_QUOTE,
                show_price="on",
                price="1200.00",
                availability=Product.Availability.IN_STOCK,
                featured="on",
            ),
        )

        self.assertRedirects(response, reverse("backoffice:product_detail", kwargs={"pk": product.pk}))
        product.refresh_from_db()
        self.assertEqual(product.name, "Produto Alterado")
        self.assertEqual(product.price, Decimal("1200.00"))
        self.assertTrue(product.featured)
        log = AuditLog.objects.get(action=AuditLog.Action.UPDATE, module="commerce.products", object_id=str(product.pk))
        self.assertEqual(log.before_data["name"], "Produto Base")
        self.assertEqual(log.after_data["name"], "Produto Alterado")

    def test_duplicate_sku_returns_form_error(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)
        self.product(sku="DUP-001")

        response = self.client.post(
            reverse("backoffice:product_create"),
            catalog_product_payload(self.category, self.brand, slug="produto-duplicado", sku="DUP-001"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Produto with this Sku already exists")

    def test_activate_deactivate_post_only_and_audits(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)
        product = self.product(active=True)

        get_response = self.client.get(reverse("backoffice:product_deactivate", kwargs={"pk": product.pk}))
        post_response = self.client.post(reverse("backoffice:product_deactivate", kwargs={"pk": product.pk}))

        self.assertEqual(get_response.status_code, 405)
        self.assertRedirects(post_response, reverse("backoffice:product_detail", kwargs={"pk": product.pk}))
        product.refresh_from_db()
        self.assertFalse(product.active)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.DEACTIVATE, object_id=str(product.pk)).exists())

    def test_permissions_for_catalog_roles(self):
        catalog = self.create_user(username="catalog-role", role=BackofficeRole.CATALOG_MANAGER)
        seller = self.create_user(username="seller-role", role=BackofficeRole.SALESPERSON)
        viewer = self.create_user(username="viewer-role", role=BackofficeRole.VIEWER)

        self.assertTrue(catalog.has_perm("commerce.change_product"))
        self.assertTrue(seller.has_perm("commerce.view_product"))
        self.assertFalse(seller.has_perm("commerce.change_product"))
        self.assertTrue(viewer.has_perm("commerce.view_product"))
        self.assertFalse(viewer.has_perm("commerce.change_product"))

    def test_salesperson_and_viewer_cannot_edit_product(self):
        product = self.product()
        seller = self.create_user(username="catalog-seller", role=BackofficeRole.SALESPERSON)
        self.client.force_login(seller)

        response = self.client.get(reverse("backoffice:product_update", kwargs={"pk": product.pk}))

        self.assertEqual(response.status_code, 403)

    def test_product_history_is_shown(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)
        product = self.product()
        AuditLog.objects.create(action=AuditLog.Action.UPDATE, module="commerce.products", object_type="Product", object_id=str(product.pk))

        response = self.client.get(reverse("backoffice:product_detail", kwargs={"pk": product.pk}))

        self.assertContains(response, "Histórico de alterações")
        self.assertContains(response, "Atualização")

    def test_category_create_update_and_audit(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)

        create_response = self.client.post(reverse("backoffice:category_create"), {"name": "Clima", "slug": "clima", "description": "Linha clima", "active": "on"})
        category = Category.objects.get(slug="clima")
        update_response = self.client.post(reverse("backoffice:category_update", kwargs={"pk": category.pk}), {"name": "Climatização", "slug": "clima", "description": "Linha clima", "active": "on"})

        self.assertRedirects(create_response, reverse("backoffice:category_list"))
        self.assertRedirects(update_response, reverse("backoffice:category_list"))
        self.assertTrue(AuditLog.objects.filter(module="commerce.categories", object_id=str(category.pk)).exists())

    def test_brand_create_update_logo_and_audit(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)

        create_response = self.client.post(reverse("backoffice:brand_create"), {"name": "Marca Nova", "slug": "marca-nova", "description": "Marca", "active": "on"}, FILES={"logo": catalog_image("logo.webp", "WEBP", "image/webp")})
        brand = Brand.objects.get(slug="marca-nova")
        update_response = self.client.post(reverse("backoffice:brand_update", kwargs={"pk": brand.pk}), {"name": "Marca Atualizada", "slug": "marca-nova", "description": "Marca", "active": "on"})

        self.assertRedirects(create_response, reverse("backoffice:brand_list"))
        self.assertRedirects(update_response, reverse("backoffice:brand_list"))
        self.assertTrue(AuditLog.objects.filter(module="commerce.brands", object_id=str(brand.pk)).exists())

    def test_product_image_upload_invalid_and_delete(self):
        self.login_role(BackofficeRole.CATALOG_MANAGER)
        product = self.product()

        upload_response = self.client.post(reverse("backoffice:product_image_create", kwargs={"pk": product.pk}), {
            "alt_text": "Imagem principal",
            "position": 0,
            "is_primary": "on",
            "image": catalog_image("produto.png", "PNG", "image/png"),
        })
        image = ProductImage.objects.get(product=product)
        invalid_response = self.client.post(reverse("backoffice:product_image_create", kwargs={"pk": product.pk}), {
            "alt_text": "Arquivo ruim",
            "position": 1,
            "image": SimpleUploadedFile("bad.txt", b"x", content_type="text/plain"),
        })
        delete_response = self.client.post(reverse("backoffice:product_image_delete", kwargs={"pk": image.pk}))

        self.assertRedirects(upload_response, reverse("backoffice:product_detail", kwargs={"pk": product.pk}))
        self.assertRedirects(invalid_response, reverse("backoffice:product_detail", kwargs={"pk": product.pk}))
        self.assertRedirects(delete_response, reverse("backoffice:product_detail", kwargs={"pk": product.pk}))
        self.assertFalse(ProductImage.objects.filter(pk=image.pk).exists())
        self.assertTrue(AuditLog.objects.filter(module="commerce.product_images", action=AuditLog.Action.CREATE).exists())
        self.assertTrue(AuditLog.objects.filter(module="commerce.product_images", action=AuditLog.Action.DELETE).exists())

    def test_image_delete_requires_permission(self):
        product = self.product()
        image = ProductImage.objects.create(product=product, image=catalog_image("foto.jpg"))
        viewer = self.create_user(username="image-viewer", role=BackofficeRole.VIEWER)
        self.client.force_login(viewer)

        response = self.client.post(reverse("backoffice:product_image_delete", kwargs={"pk": image.pk}))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ProductImage.objects.filter(pk=image.pk).exists())


class BackofficeGovernanceTests(BackofficeBaseTestCase):
    def system_admin_login(self):
        user = self.create_user(username="governance-admin", role=BackofficeRole.SYSTEM_ADMIN)
        self.client.force_login(user)
        return user

    def business_unit_payload(self, **overrides):
        data = {
            "name": "Unidade Teste",
            "code": "UNIT_TEST",
            "slug": "unit-test",
            "is_active": "on",
        }
        data.update(overrides)
        if data.get("is_active") == "":
            data.pop("is_active")
        return data


    def department_payload(self, business_unit, **overrides):
        data = {
            "business_unit": business_unit.pk,
            "name": "Comercial",
            "code": "COMERCIAL",
            "slug": "comercial",
            "is_active": "on",
        }
        data.update(overrides)
        if data.get("is_active") == "":
            data.pop("is_active")
        return data

    def team_payload(self, department, **overrides):
        data = {
            "business_unit": department.business_unit_id,
            "department": department.pk,
            "name": "Equipe Robótica",
            "code": "ROBOTICA",
            "slug": "robotica",
            "is_active": "on",
        }
        data.update(overrides)
        if data.get("is_active") == "":
            data.pop("is_active")
        return data

    def test_admin_lists_creates_edits_and_deactivates_business_unit(self):
        self.system_admin_login()

        list_response = self.client.get(reverse("backoffice:business_unit_list"))
        create_response = self.client.post(reverse("backoffice:business_unit_create"), self.business_unit_payload())
        unit = BusinessUnit.objects.get(code="UNIT_TEST")
        update_response = self.client.post(
            reverse("backoffice:business_unit_update", kwargs={"pk": unit.pk}),
            self.business_unit_payload(name="Unidade Teste Editada", code="UNIT_TEST", slug="unit-test", is_active=""),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertRedirects(create_response, reverse("backoffice:business_unit_detail", kwargs={"pk": unit.pk}))
        self.assertRedirects(update_response, reverse("backoffice:business_unit_detail", kwargs={"pk": unit.pk}))
        unit.refresh_from_db()
        self.assertEqual(unit.name, "Unidade Teste Editada")
        self.assertFalse(unit.is_active)
        self.assertTrue(AuditLog.objects.filter(module="backoffice.business_units", action=AuditLog.Action.CREATE, object_id=str(unit.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(module="backoffice.business_units", action=AuditLog.Action.DEACTIVATE, object_id=str(unit.pk)).exists())

    def test_business_unit_duplicate_code_and_slug_are_rejected(self):
        self.system_admin_login()
        BusinessUnit.objects.create(name="Existente", code="EXISTENTE", slug="existente")

        code_response = self.client.post(reverse("backoffice:business_unit_create"), self.business_unit_payload(code="EXISTENTE", slug="nova"))
        slug_response = self.client.post(reverse("backoffice:business_unit_create"), self.business_unit_payload(code="NOVA", slug="existente"))

        self.assertEqual(code_response.status_code, 200)
        self.assertContains(code_response, "Já existe uma unidade com este código.")
        self.assertEqual(slug_response.status_code, 200)
        self.assertContains(slug_response, "Já existe uma unidade com este slug.")

    def test_business_unit_management_requires_real_permissions_on_get_and_post(self):
        unit = BusinessUnit.objects.create(name="Bloqueada", code="BLOCKED", slug="blocked")
        seller = self.create_user(username="governance-seller", role=BackofficeRole.SALESPERSON)
        self.client.force_login(seller)

        list_response = self.client.get(reverse("backoffice:business_unit_list"))
        post_response = self.client.post(reverse("backoffice:business_unit_update", kwargs={"pk": unit.pk}), self.business_unit_payload(name="Alterada", code="BLOCKED", slug="blocked"))

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        unit.refresh_from_db()
        self.assertEqual(unit.name, "Bloqueada")

    def test_commercial_manager_can_view_but_not_change_business_unit(self):
        unit = BusinessUnit.objects.create(name="Somente leitura", code="READ", slug="read")
        manager = self.create_user(username="governance-manager", role=BackofficeRole.COMMERCIAL_MANAGER)
        self.client.force_login(manager)

        list_response = self.client.get(reverse("backoffice:business_unit_list"))
        post_response = self.client.post(reverse("backoffice:business_unit_update", kwargs={"pk": unit.pk}), self.business_unit_payload(name="Mudou", code="READ", slug="read"))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(post_response.status_code, 403)
        unit.refresh_from_db()
        self.assertEqual(unit.name, "Somente leitura")



    def test_admin_lists_creates_edits_and_deactivates_department(self):
        self.system_admin_login()
        unit = BusinessUnit.objects.create(name="Unidade Dept", code="DEPT_UNIT", slug="dept-unit")

        list_response = self.client.get(reverse("backoffice:department_list"))
        create_response = self.client.post(reverse("backoffice:department_create"), self.department_payload(unit))
        department = Department.objects.get(code="COMERCIAL", business_unit=unit)
        update_response = self.client.post(
            reverse("backoffice:department_update", kwargs={"pk": department.pk}),
            self.department_payload(unit, name="Comercial Editado", code="COMERCIAL", slug="comercial", is_active=""),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertRedirects(create_response, reverse("backoffice:department_list"))
        self.assertRedirects(update_response, reverse("backoffice:department_list"))
        department.refresh_from_db()
        self.assertEqual(department.name, "Comercial Editado")
        self.assertFalse(department.is_active)
        self.assertTrue(AuditLog.objects.filter(module="backoffice.departments", action=AuditLog.Action.CREATE, object_id=str(department.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(module="backoffice.departments", action=AuditLog.Action.DEACTIVATE, object_id=str(department.pk)).exists())

    def test_admin_lists_creates_edits_and_deactivates_team(self):
        self.system_admin_login()
        unit = BusinessUnit.objects.create(name="Unidade Team", code="TEAM_UNIT", slug="team-unit")
        department = Department.objects.create(business_unit=unit, name="Comercial", code="COM", slug="com")

        list_response = self.client.get(reverse("backoffice:team_list"))
        create_response = self.client.post(reverse("backoffice:team_create"), self.team_payload(department))
        team = Team.objects.get(code="ROBOTICA", department=department)
        update_response = self.client.post(
            reverse("backoffice:team_update", kwargs={"pk": team.pk}),
            self.team_payload(department, name="Equipe Robótica Editada", code="ROBOTICA", slug="robotica", is_active=""),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertRedirects(create_response, reverse("backoffice:team_list"))
        self.assertRedirects(update_response, reverse("backoffice:team_list"))
        team.refresh_from_db()
        self.assertEqual(team.name, "Equipe Robótica Editada")
        self.assertFalse(team.is_active)
        self.assertTrue(AuditLog.objects.filter(module="backoffice.teams", action=AuditLog.Action.CREATE, object_id=str(team.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(module="backoffice.teams", action=AuditLog.Action.DEACTIVATE, object_id=str(team.pk)).exists())

    def test_admin_lists_creates_updates_and_deactivates_membership(self):
        self.system_admin_login()
        user = self.create_user(username="member-user")
        unit = BusinessUnit.objects.create(name="Governança", code="GOV", slug="gov")

        list_response = self.client.get(reverse("backoffice:business_unit_membership_list"))
        create_response = self.client.post(reverse("backoffice:business_unit_membership_create"), {
            "user": user.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.OWN,
            "is_active": "on",
        })
        membership = BusinessUnitMembership.objects.get(user=user, business_unit=unit)
        update_all_response = self.client.post(reverse("backoffice:business_unit_membership_update", kwargs={"pk": membership.pk}), {
            "user": user.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.ALL,
            "is_active": "on",
        })
        update_own_response = self.client.post(reverse("backoffice:business_unit_membership_update", kwargs={"pk": membership.pk}), {
            "user": user.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.OWN,
            "is_active": "on",
        })
        deactivate_response = self.client.post(reverse("backoffice:business_unit_membership_update", kwargs={"pk": membership.pk}), {
            "user": user.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.OWN,
        })

        self.assertEqual(list_response.status_code, 200)
        self.assertRedirects(create_response, reverse("backoffice:business_unit_membership_list"))
        self.assertRedirects(update_all_response, reverse("backoffice:business_unit_membership_list"))
        self.assertRedirects(update_own_response, reverse("backoffice:business_unit_membership_list"))
        self.assertRedirects(deactivate_response, reverse("backoffice:business_unit_membership_list"))
        membership.refresh_from_db()
        self.assertEqual(membership.scope, AccessScope.OWN)
        self.assertFalse(membership.is_active)
        self.assertTrue(AuditLog.objects.filter(module="backoffice.business_unit_memberships", action=AuditLog.Action.CREATE, object_id=str(membership.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(module="backoffice.business_unit_memberships", action=AuditLog.Action.PERMISSION_CHANGED, object_id=str(membership.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(module="backoffice.business_unit_memberships", action=AuditLog.Action.DEACTIVATE, object_id=str(membership.pk)).exists())

    def test_membership_duplicate_and_incoherent_scope_links_are_rejected(self):
        self.system_admin_login()
        user = self.create_user(username="duplicate-member")
        unit = BusinessUnit.objects.create(name="Duplicada", code="DUP", slug="dup")
        other_unit = BusinessUnit.objects.create(name="Outra", code="OTHER", slug="other")
        department = Department.objects.create(business_unit=unit, name="Comercial", code="COM", slug="com")
        other_department = Department.objects.create(business_unit=other_unit, name="Outro", code="OUT", slug="out")
        team = Team.objects.create(department=department, name="Equipe", code="EQ", slug="eq")
        other_team = Team.objects.create(department=other_department, name="Outra equipe", code="OEQ", slug="oeq")
        BusinessUnitMembership.objects.create(user=user, business_unit=unit, scope=AccessScope.OWN)

        duplicate_response = self.client.post(reverse("backoffice:business_unit_membership_create"), {
            "user": user.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.ALL,
            "is_active": "on",
        })
        missing_department_response = self.client.post(reverse("backoffice:business_unit_membership_create"), {
            "user": self.create_user(username="department-member").pk,
            "business_unit": unit.pk,
            "scope": AccessScope.DEPARTMENT,
            "is_active": "on",
        })
        cross_department_response = self.client.post(reverse("backoffice:business_unit_membership_create"), {
            "user": self.create_user(username="cross-department-member").pk,
            "business_unit": unit.pk,
            "department": other_department.pk,
            "scope": AccessScope.DEPARTMENT,
            "is_active": "on",
        })
        cross_team_response = self.client.post(reverse("backoffice:business_unit_membership_create"), {
            "user": self.create_user(username="cross-team-member").pk,
            "business_unit": unit.pk,
            "department": department.pk,
            "team": other_team.pk,
            "scope": AccessScope.TEAM,
            "is_active": "on",
        })
        valid_team_response = self.client.post(reverse("backoffice:business_unit_membership_create"), {
            "user": self.create_user(username="valid-team-member").pk,
            "business_unit": unit.pk,
            "department": department.pk,
            "team": team.pk,
            "scope": AccessScope.TEAM,
            "is_active": "on",
        })

        self.assertEqual(duplicate_response.status_code, 200)
        self.assertContains(duplicate_response, "Este usuário já possui acesso configurado para esta unidade.")
        self.assertContains(missing_department_response, "Membership com escopo Departamento exige departamento.")
        self.assertContains(cross_department_response, "Select a valid choice")
        self.assertContains(cross_team_response, "Select a valid choice")
        self.assertRedirects(valid_team_response, reverse("backoffice:business_unit_membership_list"))

    def test_salesperson_and_viewer_do_not_administer_memberships(self):
        unit = BusinessUnit.objects.create(name="Protegida", code="SAFE", slug="safe")
        target = self.create_user(username="target-member")
        membership = BusinessUnitMembership.objects.create(user=target, business_unit=unit, scope=AccessScope.OWN)
        seller = self.create_user(username="membership-seller", role=BackofficeRole.SALESPERSON)
        self.client.force_login(seller)

        seller_get = self.client.get(reverse("backoffice:business_unit_membership_list"))
        seller_post = self.client.post(reverse("backoffice:business_unit_membership_update", kwargs={"pk": membership.pk}), {
            "user": target.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.ALL,
            "is_active": "on",
        })
        viewer = self.create_user(username="membership-viewer", role=BackofficeRole.VIEWER)
        self.client.force_login(viewer)
        viewer_post = self.client.post(reverse("backoffice:business_unit_membership_update", kwargs={"pk": membership.pk}), {
            "user": target.pk,
            "business_unit": unit.pk,
            "scope": AccessScope.ALL,
            "is_active": "on",
        })

        self.assertEqual(seller_get.status_code, 403)
        self.assertEqual(seller_post.status_code, 403)
        self.assertEqual(viewer_post.status_code, 403)
        membership.refresh_from_db()
        self.assertEqual(membership.scope, AccessScope.OWN)

    def test_membership_filtering_by_unit_user_scope_and_status(self):
        self.system_admin_login()
        unit = BusinessUnit.objects.create(name="Filtro", code="FILTER", slug="filter")
        user = self.create_user(username="filter-member", email="filter@example.com")
        BusinessUnitMembership.objects.create(user=user, business_unit=unit, scope=AccessScope.NONE, is_active=False)

        response = self.client.get(reverse("backoffice:business_unit_membership_list"), {
            "business_unit": unit.pk,
            "user": "filter",
            "scope": AccessScope.NONE,
            "active": "0",
        })

        self.assertContains(response, "filter@example.com")
        self.assertContains(response, "Sem acesso")
