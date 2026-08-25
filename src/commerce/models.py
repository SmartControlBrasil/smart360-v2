from decimal import Decimal
from pathlib import PurePath

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import get_valid_filename

from .seo import CANONICAL_PRODUCT_ROUTE_BY_SLUG
from PIL import Image
from PIL import UnidentifiedImageError

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_UPLOAD_SIZE = 10 * 1024 * 1024


def _safe_filename(filename):
    return get_valid_filename(PurePath(filename or "image").name)


def brand_logo_upload_path(instance, filename):
    return f"commerce/brands/{_safe_filename(filename)}"


def product_image_upload_path(instance, filename):
    slug = getattr(getattr(instance, "product", None), "slug", "") or "unassigned"
    return f"commerce/products/{slug}/{_safe_filename(filename)}"


def validate_image_upload(file):
    if not file:
        return

    name = getattr(file, "name", "")
    extension = PurePath(name).suffix.lower().lstrip(".")
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            "Envie uma imagem nos formatos JPEG, JPG, PNG ou WEBP.",
        )

    size = getattr(file, "size", None)
    if size is not None and size > MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError("A imagem deve ter no máximo 10 MB.")

    current_position = None
    if hasattr(file, "tell") and hasattr(file, "seek"):
        try:
            current_position = file.tell()
            file.seek(0)
        except OSError:
            current_position = None

    try:
        image = Image.open(file)
        image.verify()
        if image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(
                "Envie uma imagem nos formatos JPEG, JPG, PNG ou WEBP.",
            )
    except (UnidentifiedImageError, OSError):
        raise ValidationError("O arquivo enviado não é uma imagem válida.") from None
    finally:
        if current_position is not None:
            try:
                file.seek(current_position)
            except OSError:
                pass


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("commerce:category", kwargs={"slug": self.slug})


class Brand(TimeStampedModel):
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=brand_logo_upload_path, validators=[validate_image_upload], blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "marca"
        verbose_name_plural = "marcas"

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    class SaleMode(models.TextChoices):
        DIRECT = "direct", "Venda direta"
        QUOTE = "quote", "Somente orçamento"
        DIRECT_AND_QUOTE = "direct_and_quote", "Venda direta e orçamento"
        PROJECT = "project", "Projeto sob consulta"
        DEMO = "demo", "Demonstração comercial"

    class Availability(models.TextChoices):
        IN_STOCK = "in_stock", "Em estoque"
        ON_DEMAND = "on_demand", "Sob demanda"
        SUPPLIER = "supplier", "Com fornecedor"
        PRE_ORDER = "pre_order", "Pré-venda"
        CHECK_AVAILABILITY = "check_availability", "Consultar disponibilidade"

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    sku = models.CharField(max_length=80, unique=True, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name="products", null=True, blank=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    sale_mode = models.CharField(max_length=30, choices=SaleMode.choices, default=SaleMode.QUOTE)
    show_price = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    availability = models.CharField(max_length=30, choices=Availability.choices, default=Availability.CHECK_AVAILABILITY)
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}
        if self.price is not None and self.price <= Decimal("0"):
            errors["price"] = "Informe um preço maior que zero ou deixe em branco."
        if self.show_price and self.price is None:
            errors["price"] = "Produtos com preço visível precisam de preço público."
        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        return reverse("commerce:product_detail", kwargs={"slug": self.slug})

    @property
    def public_detail_url(self):
        route_name = CANONICAL_PRODUCT_ROUTE_BY_SLUG.get(self.slug)
        if route_name:
            return reverse(route_name)
        return self.get_absolute_url()

    @property
    def primary_image(self):
        return self.images.order_by("-is_primary", "position", "id").first()

    @property
    def formatted_price(self):
        if self.price is None:
            return ""
        value = f"{self.price:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {value}"

    @property
    def public_price_label(self):
        if self.show_price and self.price is not None:
            return self.formatted_price
        return ""

    @property
    def commercial_state_label(self):
        labels = {
            self.SaleMode.DIRECT: "Venda direta",
            self.SaleMode.QUOTE: "Sob orçamento",
            self.SaleMode.DIRECT_AND_QUOTE: "Venda direta / orçamento",
            self.SaleMode.PROJECT: "Projeto personalizado",
            self.SaleMode.DEMO: "Demonstração disponível",
        }
        return labels.get(self.sale_mode, "Atendimento comercial")

    @property
    def commercial_condition_label(self):
        if self.public_price_label:
            return "Preço público"
        labels = {
            self.SaleMode.DIRECT: "Consulte a disponibilidade",
            self.SaleMode.QUOTE: "Solicite um orçamento",
            self.SaleMode.DIRECT_AND_QUOTE: "Preço sob consulta",
            self.SaleMode.PROJECT: "Projeto sob consulta",
            self.SaleMode.DEMO: "Agende uma demonstração",
        }
        return labels.get(self.sale_mode, "Fale com a equipe")

    @property
    def primary_cta_label(self):
        labels = {
            self.SaleMode.DIRECT: "Comprar",
            self.SaleMode.QUOTE: "Solicitar orçamento",
            self.SaleMode.DIRECT_AND_QUOTE: "Comprar",
            self.SaleMode.PROJECT: "Solicitar projeto",
            self.SaleMode.DEMO: "Agendar demonstração",
        }
        return labels.get(self.sale_mode, "Falar com a equipe")

    @property
    def secondary_cta_label(self):
        if self.sale_mode == self.SaleMode.DIRECT_AND_QUOTE:
            return "Solicitar orçamento"
        return ""

    @property
    def primary_cta_url(self):
        route_name = CANONICAL_PRODUCT_ROUTE_BY_SLUG.get(self.slug)
        if route_name:
            return reverse(route_name)
        return f"{reverse('institutional:contact')}?produto={self.slug}&acao={self.sale_mode}"

    @property
    def secondary_cta_url(self):
        if self.secondary_cta_label:
            return f"{reverse('institutional:contact')}?produto={self.slug}&acao=orcamento"
        return ""


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_upload_path, validators=[validate_image_upload])
    alt_text = models.CharField(max_length=180, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "imagem de produto"
        verbose_name_plural = "imagens de produto"

    def __str__(self):
        return self.alt_text or self.product.name
