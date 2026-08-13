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


class CustomerBusinessRelationship(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="business_relationships",
    )
    business_unit = models.ForeignKey(
        "backoffice.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="customer_relationships",
    )
    assigned_salesperson = models.ForeignKey(
        "salespeople.Salesperson",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_relationships",
    )
    status = models.CharField(max_length=20, choices=Customer.Status.choices, default=Customer.Status.PROSPECT)
    commercial_since = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_business_relationships_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_business_relationships_updated",
    )

    class Meta:
        ordering = ["customer__legal_name", "business_unit__name"]
        constraints = [
            models.UniqueConstraint(fields=["customer", "business_unit"], name="unique_customer_business_relationship"),
        ]
        verbose_name = "relacionamento comercial do cliente"
        verbose_name_plural = "relacionamentos comerciais dos clientes"

    def __str__(self):
        return f"{self.customer} · {self.business_unit}"


class CustomerAssignmentTransfer(models.Model):
    relationship = models.ForeignKey(
        CustomerBusinessRelationship,
        on_delete=models.PROTECT,
        related_name="assignment_transfers",
    )
    previous_salesperson = models.ForeignKey(
        "salespeople.Salesperson",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assignment_transfers_from",
    )
    new_salesperson = models.ForeignKey(
        "salespeople.Salesperson",
        on_delete=models.PROTECT,
        related_name="assignment_transfers_to",
    )
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_assignment_transfers",
    )
    reason = models.TextField()
    transferred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-transferred_at", "-id"]
        permissions = [
            ("transfer_customerassignment", "Pode transferir responsável comercial"),
        ]
        verbose_name = "transferência de responsável comercial"
        verbose_name_plural = "transferências de responsáveis comerciais"

    def __str__(self):
        return f"{self.relationship} · {self.previous_salesperson} -> {self.new_salesperson}"

    def clean(self):
        if not (self.reason or "").strip():
            from django.core.exceptions import ValidationError

            raise ValidationError({"reason": "Informe o motivo da transferência."})

    def save(self, *args, **kwargs):
        if self.pk and CustomerAssignmentTransfer.objects.filter(pk=self.pk).exists():
            raise ValueError("Transferências registradas são append-only e não podem ser alteradas.")
        self.reason = (self.reason or "").strip()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Transferências registradas não podem ser excluídas pela aplicação.")
