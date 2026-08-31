from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MarketSegment(TimeStampedModel):
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "segmento de mercado"
        verbose_name_plural = "segmentos de mercado"

    def __str__(self):
        return self.name


class ProspectingCampaign(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        ACTIVE = "ACTIVE", "Ativa"
        PAUSED = "PAUSED", "Pausada"
        COMPLETED = "COMPLETED", "Concluída"
        ARCHIVED = "ARCHIVED", "Arquivada"

    name = models.CharField(max_length=180)
    product = models.ForeignKey(
        "commerce.Product",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="prospecting_campaigns",
    )
    market_segment = models.ForeignKey(
        MarketSegment,
        on_delete=models.PROTECT,
        related_name="prospecting_campaigns",
    )
    location_description = models.CharField(max_length=180)
    objective = models.CharField(max_length=180)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_intelligence_campaigns_created",
    )

    class Meta:
        ordering = ["-created_at", "name"]
        verbose_name = "campanha de prospecção"
        verbose_name_plural = "campanhas de prospecção"

    def __str__(self):
        return self.name


class SearchRun(TimeStampedModel):
    class Source(models.TextChoices):
        GOOGLE_MAPS = "GOOGLE_MAPS", "Google Maps"
        GOOGLE_SEARCH = "GOOGLE_SEARCH", "Google Search"
        MANUAL = "MANUAL", "Manual"
        IMPORT = "IMPORT", "Importação"
        OTHER = "OTHER", "Outro"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        RUNNING = "RUNNING", "Em execução"
        COMPLETED = "COMPLETED", "Concluída"
        FAILED = "FAILED", "Falhou"
        CANCELLED = "CANCELLED", "Cancelada"

    campaign = models.ForeignKey(
        ProspectingCampaign,
        on_delete=models.PROTECT,
        related_name="search_runs",
    )
    query = models.CharField(max_length=180)
    location = models.CharField(max_length=180, blank=True)
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.GOOGLE_MAPS, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    requested_limit = models.PositiveIntegerField(null=True, blank=True)
    total_found = models.PositiveIntegerField(default=0)
    total_new = models.PositiveIntegerField(default=0)
    total_existing = models.PositiveIntegerField(default=0)
    total_rejected = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_intelligence_search_runs_created",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["campaign", "status", "created_at"], name="si_run_campaign_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(requested_limit__isnull=True) | Q(requested_limit__gt=0),
                name="sales_intelligence_searchrun_requested_limit_positive",
            ),
            models.CheckConstraint(
                condition=Q(finished_at__isnull=True) | Q(started_at__isnull=True) | Q(finished_at__gte=models.F("started_at")),
                name="sales_intelligence_searchrun_finished_after_started",
            ),
        ]
        verbose_name = "execução de pesquisa"
        verbose_name_plural = "execuções de pesquisa"

    def __str__(self):
        suffix = f" · {self.location}" if self.location else ""
        return f"{self.campaign} · {self.query}{suffix}"

    def clean(self):
        errors = {}
        if self.finished_at and self.started_at and self.finished_at < self.started_at:
            errors["finished_at"] = "A finalização não pode ser anterior ao início."
        if self.status == self.Status.RUNNING and not self.started_at:
            errors["started_at"] = "Pesquisas em execução precisam de data de início."
        if self.status in {self.Status.COMPLETED, self.Status.FAILED, self.Status.CANCELLED} and not self.finished_at:
            errors["finished_at"] = "Status final exige data de finalização."
        if errors:
            raise ValidationError(errors)


class SearchResult(TimeStampedModel):
    class ProcessingStatus(models.TextChoices):
        DISCOVERED = "DISCOVERED", "Descoberto"
        LINKED = "LINKED", "Vinculado"
        CREATED = "CREATED", "Cliente criado"
        DUPLICATE = "DUPLICATE", "Duplicado"
        REJECTED = "REJECTED", "Rejeitado"
        ERROR = "ERROR", "Erro"

    search_run = models.ForeignKey(
        SearchRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    name = models.CharField(max_length=180)
    phone = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=2, blank=True)
    source_url = models.URLField(blank=True)
    source_url_key = models.CharField(max_length=255, blank=True, editable=False)
    external_id = models.CharField(max_length=180, blank=True)
    name_phone_key = models.CharField(max_length=255, blank=True, editable=False)
    raw_data = models.JSONField(default=dict, blank=True)
    customer = models.ForeignKey(
        "customers.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_intelligence_search_results",
    )
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.DISCOVERED,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["search_run", "processing_status"], name="si_result_run_status_idx"),
            models.Index(fields=["customer"], name="si_result_customer_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["search_run", "external_id"],
                condition=~Q(external_id=""),
                name="unique_search_result_external_id_per_run",
            ),
            models.UniqueConstraint(
                fields=["search_run", "source_url_key"],
                condition=~Q(source_url_key=""),
                name="unique_search_result_source_url_per_run",
            ),
            models.UniqueConstraint(
                fields=["search_run", "name_phone_key"],
                condition=~Q(name_phone_key=""),
                name="unique_search_result_name_phone_per_run",
            ),
            models.CheckConstraint(
                condition=Q(processing_status__in=["DISCOVERED", "DUPLICATE", "REJECTED", "ERROR"]) | Q(customer__isnull=False),
                name="sales_intelligence_processed_result_requires_customer",
            ),
        ]
        verbose_name = "resultado de pesquisa"
        verbose_name_plural = "resultados de pesquisa"

    def __str__(self):
        return self.name

    def clean(self):
        if self.state:
            self.state = self.state.upper()
        if self.processing_status in {self.ProcessingStatus.LINKED, self.ProcessingStatus.CREATED} and not self.customer_id:
            raise ValidationError({"customer": "Resultados vinculados ou criados exigem um cliente."})

    def save(self, *args, **kwargs):
        if self.state:
            self.state = self.state.upper()
        return super().save(*args, **kwargs)


class CampaignProspect(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "NEW", "Novo"
        REVIEWED = "REVIEWED", "Revisado"
        CONTACT_READY = "CONTACT_READY", "Pronto para contato"
        DISCARDED = "DISCARDED", "Descartado"

    campaign = models.ForeignKey(
        ProspectingCampaign,
        on_delete=models.CASCADE,
        related_name="prospects",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="sales_intelligence_campaign_prospects",
    )
    origin_search_result = models.ForeignKey(
        SearchResult,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="campaign_prospect_origins",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_intelligence_campaign_prospects_created",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["campaign", "status"], name="si_cp_campaign_status_idx"),
            models.Index(fields=["customer"], name="si_prospect_customer_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "customer"], name="unique_campaign_prospect_customer"),
        ]
        verbose_name = "prospect de campanha"
        verbose_name_plural = "prospects de campanha"

    def __str__(self):
        return f"{self.campaign} · {self.customer}"
