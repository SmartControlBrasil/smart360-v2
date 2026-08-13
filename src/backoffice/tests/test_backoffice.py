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
