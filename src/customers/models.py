import re

from django.conf import settings
from django.db import models
from django.db.models import Q


def only_digits(value):
    return re.sub(r"\D", "", value or "")


class Customer(models.Model):
    class CustomerType(models.TextChoices):
        COMPANY = "COMPANY", "Empresa"
        INDIVIDUAL = "INDIVIDUAL", "Pessoa física"
        PUBLIC_ORGANIZATION = "PUBLIC_ORGANIZATION", "Órgão público"
        SCHOOL = "SCHOOL", "Escola"
        CONDOMINIUM = "CONDOMINIUM", "Condomínio"
        OTHER = "OTHER", "Outro"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativo"
        INACTIVE = "INACTIVE", "Inativo"
        PROSPECT = "PROSPECT", "Prospect"

    customer_type = models.CharField(max_length=30, choices=CustomerType.choices, default=CustomerType.COMPANY)
    legal_name = models.CharField(max_length=180)
    trade_name = models.CharField(max_length=180, blank=True)
    document = models.CharField(max_length=20, blank=True, null=True)
    state_registration = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    postal_code = models.CharField(max_length=12, blank=True)
    address_line = models.CharField(max_length=180, blank=True)
    address_number = models.CharField(max_length=30, blank=True)
    address_extra = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=2, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROSPECT)
    assigned_salesperson = models.ForeignKey(
        "salespeople.Salesperson",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customers_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customers_updated",
    )

    class Meta:
        ordering = ["legal_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["document"],
                condition=Q(document__isnull=False) & ~Q(document=""),
                name="unique_customer_document_when_present",
            ),
        ]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.trade_name or self.legal_name

    def clean(self):
        if self.document:
            self.document = only_digits(self.document)
        if self.state:
            self.state = self.state.upper()

    def save(self, *args, **kwargs):
        if self.document:
            self.document = only_digits(self.document)
        else:
            self.document = None
        if self.state:
            self.state = self.state.upper()
        super().save(*args, **kwargs)
