from decimal import Decimal
from io import BytesIO
import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Brand
from .models import Category
from .models import Product
from .models import ProductImage


TEST_MODEL_MEDIA_ROOT = tempfile.mkdtemp()
TEST_MEDIA_ROOT = tempfile.mkdtemp()


def image_upload(name="image.jpg", image_format="JPEG", content_type="image/jpeg"):
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


@override_settings(MEDIA_ROOT=TEST_MODEL_MEDIA_ROOT)
class CommerceModelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MODEL_MEDIA_ROOT, ignore_errors=True)

    def test_category_creation(self):
        category = Category.objects.create(name="Robótica", slug="robotica")

        self.assertEqual(str(category), "Robótica")
        self.assertTrue(category.active)

    def test_brand_creation(self):
        brand = Brand.objects.create(name="Xyron", slug="xyron")

        self.assertEqual(str(brand), "Xyron")
        self.assertTrue(brand.active)

    def test_product_creation(self):
        category = Category.objects.create(name="Automação", slug="automacao")
        brand = Brand.objects.create(name="Smart Control", slug="smart-control")
        product = Product.objects.create(
            name="Controlador Industrial",
            slug="controlador-industrial",
            sku="SCB-001",
            category=category,
            brand=brand,
            sale_mode=Product.SaleMode.QUOTE,
        )

        self.assertEqual(str(product), "Controlador Industrial")
        self.assertEqual(product.category, category)
        self.assertEqual(product.brand, brand)

    def test_product_without_price_is_valid_when_price_is_hidden(self):
        category = Category.objects.create(name="Projetos", slug="projetos")
        product = Product(
            name="Projeto Especial",
            slug="projeto-especial",
            category=category,
            sale_mode=Product.SaleMode.PROJECT,
            show_price=False,
            price=None,
        )

        product.full_clean()

    def test_visible_price_requires_price(self):
        category = Category.objects.create(name="Peças", slug="pecas")
        product = Product(
            name="Peça Técnica",
            slug="peca-tecnica",
            category=category,
            show_price=True,
            price=None,
        )

        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_brand_logo_accepts_valid_image(self):
        brand = Brand(
            name="Imagem Brand",
            slug="imagem-brand",
            logo=image_upload("logo.webp", image_format="WEBP", content_type="image/webp"),
        )

        brand.full_clean()

    def test_product_image_accepts_valid_image(self):
        category = Category.objects.create(name="Imagens", slug="imagens")
        product = Product.objects.create(name="Produto com Imagem", slug="produto-com-imagem", category=category)
        product_image = ProductImage(
            product=product,
            image=image_upload("produto.png", image_format="PNG", content_type="image/png"),
        )

        product_image.full_clean()

    def test_non_image_file_is_rejected(self):
        category = Category.objects.create(name="Arquivos", slug="arquivos")
        product = Product.objects.create(name="Produto Arquivo", slug="produto-arquivo", category=category)
        product_image = ProductImage(
            product=product,
            image=SimpleUploadedFile("arquivo.txt", b"nao sou imagem", content_type="text/plain"),
        )

        with self.assertRaises(ValidationError):
            product_image.full_clean()

    def test_oversized_image_is_rejected(self):
        category = Category.objects.create(name="Grandes", slug="grandes")
        product = Product.objects.create(name="Produto Grande", slug="produto-grande", category=category)
        product_image = ProductImage(
            product=product,
            image=SimpleUploadedFile("grande.jpg", b"0" * (10 * 1024 * 1024 + 1), content_type="image/jpeg"),
        )

        with self.assertRaises(ValidationError):
            product_image.full_clean()

    def test_upload_does_not_break_product(self):
        category = Category.objects.create(name="Upload", slug="upload")
        product = Product.objects.create(name="Produto Upload", slug="produto-upload", category=category)
        product_image = ProductImage.objects.create(
            product=product,
            image=image_upload("foto.jpg"),
            is_primary=True,
        )

        self.assertEqual(product.primary_image, product_image)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CommercePublicViewsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.category = Category.objects.create(name="Robótica", slug="robotica")
        self.other_category = Category.objects.create(name="Climatização", slug="climatizacao")
        self.refrigeration_category = Category.objects.create(name="Refrigeração", slug="refrigeracao")
        self.automation_category = Category.objects.create(name="Automação Industrial", slug="automacao-industrial")
        self.brand = Brand.objects.create(name="Xyron Robotics", slug="xyron-robotics")
        self.mitsubishi_brand = Brand.objects.create(name="Mitsubishi Electric", slug="mitsubishi-electric")
        self.active_product = Product.objects.create(
            name="Xyron Demo",
            slug="xyron-demo",
            sku="XYR-DEMO",
            category=self.category,
            brand=self.brand,
            short_description="Robô demonstrativo para validação pública.",
            sale_mode=Product.SaleMode.DEMO,
            availability=Product.Availability.ON_DEMAND,
        )
        self.inactive_product = Product.objects.create(
            name="Produto Inativo",
            slug="produto-inativo",
            category=self.category,
            active=False,
        )
        self.other_product = Product.objects.create(
            name="Ar-condicionado",
            slug="ar-condicionado",
            category=self.other_category,
            show_price=True,
            price=Decimal("1200.00"),
            sale_mode=Product.SaleMode.DIRECT_AND_QUOTE,
            availability=Product.Availability.IN_STOCK,
        )
        self.quote_product = Product.objects.create(
            name="Produto Mitsubishi",
            slug="produto-mitsubishi",
            category=self.automation_category,
            brand=self.mitsubishi_brand,
            sale_mode=Product.SaleMode.QUOTE,
            show_price=False,
        )
        self.project_product = Product.objects.create(
            name="Câmara frigorífica",
            slug="camara-frigorifica",
            category=self.refrigeration_category,
            sale_mode=Product.SaleMode.PROJECT,
            show_price=False,
        )

    def test_shop_responds_200(self):
        response = self.client.get(reverse("commerce:shop"))

        self.assertEqual(response.status_code, 200)

    def test_active_product_appears_in_shop(self):
        response = self.client.get(reverse("commerce:shop"))

        self.assertContains(response, self.active_product.name)

    def test_inactive_product_does_not_appear_in_shop(self):
        response = self.client.get(reverse("commerce:shop"))

        self.assertNotContains(response, self.inactive_product.name)

    def test_product_detail_responds_by_slug(self):
        response = self.client.get(self.active_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_product.name)
        self.assertContains(response, "Agendar demonstração")

    def test_category_filters_products(self):
        response = self.client.get(self.category.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_product.name)
        self.assertNotContains(response, self.other_product.name)

    def test_product_without_image_remains_accessible(self):
        response = self.client.get(self.active_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_product.name)

    def test_product_with_image_renders_media_url(self):
        ProductImage.objects.create(
            product=self.active_product,
            image=image_upload("catalogo.jpg"),
            alt_text="Imagem do catálogo",
            is_primary=True,
        )

        response = self.client.get(reverse("commerce:shop"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/media/commerce/products/xyron-demo/")
        self.assertContains(response, "Imagem do catálogo")


    def test_product_detail_social_metadata_uses_primary_image(self):
        ProductImage.objects.create(
            product=self.active_product,
            image=image_upload("principal.jpg"),
            alt_text="Imagem principal Xyron Demo",
            is_primary=True,
        )

        response = self.client.get(self.active_product.get_absolute_url())
        html = response.content.decode()

        self.assertContains(response, '<meta property="og:title" content="Xyron Demo | Smart Control Brasil">')
        self.assertContains(
            response,
            '<meta property="og:description" content="Robô demonstrativo para validação pública.">',
        )
        self.assertContains(
            response,
            '<meta property="og:url" content="https://www.smartcontrolbrasil.com.br/loja/produto/xyron-demo/">',
        )
        self.assertContains(response, '<meta property="og:type" content="website">')
        self.assertIn('content="https://www.smartcontrolbrasil.com.br/media/commerce/products/xyron-demo/', html)
        self.assertContains(response, '<meta name="twitter:card" content="summary_large_image">')
        self.assertContains(response, '<meta name="twitter:title" content="Xyron Demo | Smart Control Brasil">')
        self.assertNotIn('content="/media/', html)

    def test_product_detail_social_metadata_uses_fallback_without_image(self):
        response = self.client.get(self.active_product.get_absolute_url())
        fallback_image = "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/banner-6-img-1.png"

        self.assertContains(response, f'<meta property="og:image" content="{fallback_image}">')
        self.assertContains(response, f'<meta name="twitter:image" content="{fallback_image}">')

    def test_price_appears_when_allowed(self):
        response = self.client.get(reverse("commerce:shop"))

        self.assertContains(response, "R$ 1.200,00")
        self.assertContains(response, "Venda direta / orçamento")

    def test_price_does_not_appear_when_hidden(self):
        response = self.client.get(self.active_product.get_absolute_url())

        self.assertNotContains(response, "R$ 0,00")
        self.assertNotContains(response, "R$ 0.00")
        self.assertNotContains(response, "Preço sob consulta")
        self.assertContains(response, "Agende uma demonstração")

    def test_quote_product_shows_quote_cta(self):
        response = self.client.get(self.quote_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar orçamento")
        self.assertContains(response, "Sob orçamento")
        self.assertContains(response, "Mitsubishi Electric")

    def test_demo_product_shows_demo_cta(self):
        response = self.client.get(self.active_product.get_absolute_url())

        self.assertContains(response, "Agendar demonstração")
        self.assertContains(response, "Demonstração disponível")

    def test_project_product_shows_project_cta(self):
        response = self.client.get(self.project_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar projeto")
        self.assertContains(response, "Projeto personalizado")
        self.assertContains(response, "Projeto sob consulta")

    def test_direct_and_quote_product_shows_both_ctas(self):
        response = self.client.get(self.other_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comprar")
        self.assertContains(response, "Solicitar orçamento")
        self.assertContains(response, "R$ 1.200,00")

    def test_product_detail_hides_empty_technical_tab(self):
        response = self.client.get(self.active_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Informações técnicas")
        self.assertNotContains(response, "Informações técnicas serão apresentadas")

    def test_product_with_multiple_images_renders_gallery(self):
        ProductImage.objects.create(
            product=self.active_product,
            image=image_upload("principal.jpg"),
            alt_text="Imagem principal LittleBot",
            is_primary=True,
            position=0,
        )
        ProductImage.objects.create(
            product=self.active_product,
            image=image_upload("detalhe.jpg"),
            alt_text="Imagem adicional LittleBot",
            position=1,
        )

        response = self.client.get(self.active_product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Imagem principal LittleBot", count=2)
        self.assertContains(response, "Imagem adicional LittleBot")
        self.assertContains(response, "commerce-thumb-list")

    def test_missing_product_returns_404(self):
        response = self.client.get(reverse("commerce:product_detail", kwargs={"slug": "nao-existe"}))

        self.assertEqual(response.status_code, 404)
