import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog
from src.backoffice.services.audit_helpers import model_snapshot
from src.customers.forms import CustomerForm
from src.customers.models import Customer
from src.customers.services import CUSTOMER_AUDIT_FIELDS
from src.customers.services import create_customer
from src.customers.services import sync_default_customer_relationship
from src.sales_intelligence.models import CampaignProspect
from src.sales_intelligence.models import ProspectingCampaign
from src.sales_intelligence.models import SearchResult
from src.sales_intelligence.models import SearchRun


MAX_BATCH_RESULTS = 100
MAX_FAILURE_REASON_LENGTH = 255
MARKET_SEGMENT_AUDIT_FIELDS = ["name", "slug", "description", "is_active"]
CAMPAIGN_AUDIT_FIELDS = ["name", "product", "market_segment", "location_description", "objective", "status", "created_by"]
SEARCH_RUN_AUDIT_FIELDS = [
    "campaign", "query", "location", "source", "status", "requested_limit", "total_found",
    "total_new", "total_existing", "total_rejected", "started_at", "finished_at", "failure_reason", "created_by",
]
SEARCH_RESULT_AUDIT_FIELDS = [
    "search_run", "name", "phone", "website", "address", "city", "state", "source_url",
    "source_url_key", "external_id", "name_phone_key", "raw_data", "customer", "processing_status",
]
CAMPAIGN_PROSPECT_AUDIT_FIELDS = [
    "campaign", "customer", "origin_search_result", "status", "notes", "created_by",
]
FINAL_SEARCH_RUN_STATUSES = {SearchRun.Status.COMPLETED, SearchRun.Status.FAILED, SearchRun.Status.CANCELLED}
_ALLOWED_FINAL_TRANSITIONS = {
    SearchRun.Status.RUNNING: FINAL_SEARCH_RUN_STATUSES,
}
_url_validator = URLValidator()


class IngestionError(Exception):
    status_code = 400

    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


class IngestionConflict(IngestionError):
    status_code = 409


class ConsolidationError(Exception):
    status_code = 400

    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


class ConsolidationConflict(ConsolidationError):
    status_code = 409


class MatchStatus(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"


class MatchReason(StrEnum):
    PHONE = "PHONE"
    WEBSITE_DOMAIN = "WEBSITE_DOMAIN"
    NAME_PHONE = "NAME_PHONE"
    NAME_WEBSITE_DOMAIN = "NAME_WEBSITE_DOMAIN"


@dataclass(frozen=True)
class CustomerMatchCandidate:
    customer: Customer
    reasons: tuple[str, ...]

    def as_dict(self):
        return {
            "customer_id": self.customer.pk,
            "display_name": self.customer.display_name,
            "legal_name": self.customer.legal_name,
            "trade_name": self.customer.trade_name,
            "document": self.customer.document,
            "phone": self.customer.phone,
            "whatsapp": self.customer.whatsapp,
            "website": self.customer.website,
            "city": self.customer.city,
            "state": self.customer.state,
            "status": self.customer.status,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CustomerMatchResult:
    status: str
    candidates: tuple[CustomerMatchCandidate, ...]

    def as_dict(self):
        return {
            "status": self.status,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }


def _actor_from_request(request):
    actor = getattr(request, "user", None) if request is not None else None
    return actor if getattr(actor, "is_authenticated", False) else None


def _record_create(*, instance, module, fields, request=None, actor=None):
    AuditService.record(
        action=AuditLog.Action.CREATE,
        module=module,
        request=request,
        actor=actor or _actor_from_request(request),
        object_type=instance.__class__.__name__,
        object_id=instance.pk,
        object_repr=str(instance),
        after_data=model_snapshot(instance, fields),
    )


def _record_update(*, instance, module, fields, before, request=None, actor=None, metadata=None):
    AuditService.record(
        action=AuditLog.Action.UPDATE,
        module=module,
        request=request,
        actor=actor or _actor_from_request(request),
        object_type=instance.__class__.__name__,
        object_id=instance.pk,
        object_repr=str(instance),
        before_data=before,
        after_data=model_snapshot(instance, fields),
        metadata=metadata or {},
    )


def normalize_spaces(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_phone_for_match(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    return digits


def normalize_url_for_match(value):
    value = (value or "").strip()
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if not scheme or not netloc:
        return ""
    return urlunsplit((scheme, netloc, path, "", ""))


def normalize_name_for_match(value):
    return normalize_spaces(value).casefold()


def normalize_domain_for_match(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    domain = (parsed.netloc or "").split("@")[-1].lower()
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _customer_names_for_match(customer):
    names = {normalize_name_for_match(customer.legal_name), normalize_name_for_match(customer.trade_name)}
    return {name for name in names if name}


def _customer_phones_for_match(customer):
    phones = {normalize_phone_for_match(customer.phone), normalize_phone_for_match(customer.whatsapp)}
    return {phone for phone in phones if phone}


def find_customer_matches(search_result):
    result_name = normalize_name_for_match(search_result.name)
    result_phone = normalize_phone_for_match(search_result.phone)
    result_domain = normalize_domain_for_match(search_result.website)
    candidate_map = {}

    if not result_phone and not result_domain:
        return CustomerMatchResult(MatchStatus.NO_MATCH, tuple())

    queryset = Customer.objects.all().only(
        "id", "legal_name", "trade_name", "document", "phone", "whatsapp", "website", "city", "state", "status"
    )
    for customer in queryset.order_by("id"):
        reasons = []
        customer_phones = _customer_phones_for_match(customer)
        customer_domain = normalize_domain_for_match(customer.website)
        names_match = bool(result_name and result_name in _customer_names_for_match(customer))
        phone_match = bool(result_phone and result_phone in customer_phones)
        domain_match = bool(result_domain and result_domain == customer_domain)
        if phone_match:
            reasons.append(MatchReason.PHONE)
        if domain_match:
            reasons.append(MatchReason.WEBSITE_DOMAIN)
        if names_match and phone_match:
            reasons.append(MatchReason.NAME_PHONE)
        if names_match and domain_match:
            reasons.append(MatchReason.NAME_WEBSITE_DOMAIN)
        if reasons:
            candidate_map[customer.pk] = CustomerMatchCandidate(customer=customer, reasons=tuple(str(reason) for reason in reasons))

    candidates = tuple(candidate_map.values())
    if len(candidates) == 1:
        return CustomerMatchResult(MatchStatus.EXACT_MATCH, candidates)
    if len(candidates) > 1:
        return CustomerMatchResult(MatchStatus.AMBIGUOUS, candidates)
    return CustomerMatchResult(MatchStatus.NO_MATCH, tuple())


def _ensure_campaign_prospect(*, campaign, customer, origin_search_result=None, actor=None, request=None):
    prospect, created = CampaignProspect.objects.get_or_create(
        campaign=campaign,
        customer=customer,
        defaults={
            "origin_search_result": origin_search_result,
            "created_by": actor if getattr(actor, "is_authenticated", False) else None,
        },
    )
    if created:
        _record_create(
            instance=prospect,
            module="sales_intelligence.campaign_prospects",
            fields=CAMPAIGN_PROSPECT_AUDIT_FIELDS,
            request=request,
            actor=actor,
        )
        return prospect, True
    if origin_search_result and prospect.origin_search_result_id is None:
        before = model_snapshot(prospect, CAMPAIGN_PROSPECT_AUDIT_FIELDS)
        prospect.origin_search_result = origin_search_result
        prospect.save(update_fields=["origin_search_result", "updated_at"])
        _record_update(
            instance=prospect,
            module="sales_intelligence.campaign_prospects",
            fields=CAMPAIGN_PROSPECT_AUDIT_FIELDS,
            before=before,
            request=request,
            actor=actor,
            metadata={"event": "origin_search_result_attached"},
        )
    return prospect, False


def link_search_result_to_customer(*, search_result, customer, actor=None, request=None):
    actor = actor or _actor_from_request(request)
    with transaction.atomic():
        locked_result = SearchResult.objects.select_for_update(of=("self",)).select_related("search_run__campaign", "customer").get(pk=search_result.pk)
        locked_customer = Customer.objects.select_for_update().get(pk=customer.pk)
        if locked_result.customer_id and locked_result.customer_id != locked_customer.pk:
            raise ConsolidationConflict({"customer_id": "Resultado já consolidado com outro cliente."})
        before = model_snapshot(locked_result, SEARCH_RESULT_AUDIT_FIELDS)
        changed = locked_result.customer_id != locked_customer.pk or locked_result.processing_status != SearchResult.ProcessingStatus.LINKED
        locked_result.customer = locked_customer
        locked_result.processing_status = SearchResult.ProcessingStatus.LINKED
        locked_result.full_clean()
        locked_result.save(update_fields=["customer", "processing_status", "updated_at"])
        prospect, _ = _ensure_campaign_prospect(
            campaign=locked_result.search_run.campaign,
            customer=locked_customer,
            origin_search_result=locked_result,
            actor=actor,
            request=request,
        )
        _sync_search_run_counters(locked_result.search_run)
        locked_result.search_run.save(update_fields=["total_found", "total_new", "total_existing", "total_rejected", "updated_at"])
        if changed:
            _record_update(
                instance=locked_result,
                module="sales_intelligence.search_results",
                fields=SEARCH_RESULT_AUDIT_FIELDS,
                before=before,
                request=request,
                actor=actor,
                metadata={"event": "customer_linked", "customer_id": locked_customer.pk, "campaign_prospect_id": prospect.pk},
            )
        return locked_result, prospect


def _customer_initial_data_from_search_result(search_result):
    name = normalize_spaces(search_result.name)
    return {
        "customer_type": Customer.CustomerType.COMPANY,
        "legal_name": name,
        "trade_name": name,
        "document": "",
        "state_registration": "",
        "email": "",
        "phone": normalize_spaces(search_result.phone),
        "whatsapp": "",
        "website": normalize_spaces(search_result.website),
        "postal_code": "",
        "address_line": normalize_spaces(search_result.address),
        "address_number": "",
        "address_extra": "",
        "district": "",
        "city": normalize_spaces(search_result.city),
        "state": normalize_spaces(search_result.state).upper(),
        "assigned_salesperson": "",
        "status": Customer.Status.PROSPECT,
        "notes": "Criado a partir de resultado de prospecção do Sales Intelligence. Nome legal não verificado.",
    }


def create_customer_from_search_result(*, search_result, actor=None, request=None):
    actor = actor or _actor_from_request(request)
    with transaction.atomic():
        locked_result = SearchResult.objects.select_for_update(of=("self",)).select_related("search_run__campaign", "customer").get(pk=search_result.pk)
        if locked_result.customer_id:
            if locked_result.processing_status == SearchResult.ProcessingStatus.CREATED:
                prospect, _ = _ensure_campaign_prospect(
                    campaign=locked_result.search_run.campaign,
                    customer=locked_result.customer,
                    origin_search_result=locked_result,
                    actor=actor,
                    request=request,
                )
                return locked_result.customer, locked_result, prospect
            raise ConsolidationConflict({"customer_id": "Resultado já consolidado com cliente existente."})
        customer_form = CustomerForm(data=_customer_initial_data_from_search_result(locked_result), user=actor)
        if not customer_form.is_valid():
            raise ConsolidationError(customer_form.errors.get_json_data())
        if request is not None:
            customer = create_customer(form=customer_form, request=request)
        else:
            customer = customer_form.save(commit=False)
            customer.created_by = actor if getattr(actor, "is_authenticated", False) else None
            customer.updated_by = actor if getattr(actor, "is_authenticated", False) else None
            customer.save()
            sync_default_customer_relationship(customer=customer, request=request)
            _record_create(instance=customer, module="customers", fields=CUSTOMER_AUDIT_FIELDS, request=request, actor=actor)
        before = model_snapshot(locked_result, SEARCH_RESULT_AUDIT_FIELDS)
        locked_result.customer = customer
        locked_result.processing_status = SearchResult.ProcessingStatus.CREATED
        locked_result.full_clean()
        locked_result.save(update_fields=["customer", "processing_status", "updated_at"])
        prospect, _ = _ensure_campaign_prospect(
            campaign=locked_result.search_run.campaign,
            customer=customer,
            origin_search_result=locked_result,
            actor=actor,
            request=request,
        )
        _sync_search_run_counters(locked_result.search_run)
        locked_result.search_run.save(update_fields=["total_found", "total_new", "total_existing", "total_rejected", "updated_at"])
        _record_update(
            instance=locked_result,
            module="sales_intelligence.search_results",
            fields=SEARCH_RESULT_AUDIT_FIELDS,
            before=before,
            request=request,
            actor=actor,
            metadata={"event": "customer_created", "customer_id": customer.pk, "campaign_prospect_id": prospect.pk},
        )
        return customer, locked_result, prospect


def campaign_prospect_payload(prospect):
    return {
        "id": prospect.pk,
        "campaign_id": prospect.campaign_id,
        "customer_id": prospect.customer_id,
        "origin_search_result_id": prospect.origin_search_result_id,
        "status": prospect.status,
    }


def _validate_url(field, value, errors):
    if not value:
        return
    try:
        _url_validator(value)
    except ValidationError:
        errors[field] = "Informe uma URL válida."


def _validate_choice(field, value, choices, errors):
    valid_values = {choice[0] for choice in choices}
    if value not in valid_values:
        errors[field] = "Valor inválido."


def _validation_error_dict(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": exc.messages}


def _sync_search_run_counters(search_run):
    results = search_run.results.all()
    total_found = results.exclude(processing_status=SearchResult.ProcessingStatus.REJECTED).count()
    total_rejected = results.filter(processing_status=SearchResult.ProcessingStatus.REJECTED).count()
    total_existing = results.filter(processing_status=SearchResult.ProcessingStatus.LINKED).count()
    total_new = results.filter(processing_status__in=[
        SearchResult.ProcessingStatus.DISCOVERED,
        SearchResult.ProcessingStatus.CREATED,
    ]).count()
    search_run.total_found = total_found
    search_run.total_new = total_new
    search_run.total_existing = total_existing
    search_run.total_rejected = total_rejected
    return search_run


def _normalize_result_payload(item):
    errors = {}
    if not isinstance(item, dict):
        raise IngestionError({"results": "Cada item precisa ser um objeto."})

    raw_name = item.get("name", "")
    name = normalize_spaces(raw_name)
    if not name:
        errors["name"] = "Informe o nome do resultado."

    fields = {
        "phone": normalize_spaces(item.get("phone", "")),
        "website": normalize_spaces(item.get("website", "")),
        "address": normalize_spaces(item.get("address", "")),
        "city": normalize_spaces(item.get("city", "")),
        "state": normalize_spaces(item.get("state", "")).upper(),
        "source_url": normalize_spaces(item.get("source_url", "")),
        "external_id": normalize_spaces(item.get("external_id", "")),
    }
    max_lengths = {
        "name": 180, "phone": 40, "website": 200, "address": 255, "city": 120,
        "state": 2, "source_url": 200, "external_id": 180,
    }
    for field, limit in max_lengths.items():
        value = name if field == "name" else fields[field]
        if len(value) > limit:
            errors[field] = f"Use no máximo {limit} caracteres."
    if fields["state"] and len(fields["state"]) != 2:
        errors["state"] = "Use a sigla com 2 caracteres."
    _validate_url("website", fields["website"], errors)
    _validate_url("source_url", fields["source_url"], errors)

    raw_data = item.get("raw_data", {})
    if raw_data is None:
        raw_data = {}
    if not isinstance(raw_data, dict):
        errors["raw_data"] = "raw_data precisa ser um objeto JSON."

    if errors:
        raise IngestionError(errors)

    phone_key = normalize_phone_for_match(fields["phone"])
    normalized_name = name.casefold()
    source_url_key = normalize_url_for_match(fields["source_url"])
    name_phone_key = f"{normalized_name}|{phone_key}" if phone_key else ""

    return {
        "name": name,
        **fields,
        "raw_data": raw_data,
        "source_url_key": source_url_key,
        "name_phone_key": name_phone_key,
    }


def _find_duplicate(search_run, payload):
    candidates = SearchResult.objects.filter(search_run=search_run)
    if payload["external_id"]:
        duplicate = candidates.filter(external_id=payload["external_id"]).first()
        if duplicate:
            return duplicate
    if payload["source_url_key"]:
        duplicate = candidates.filter(source_url_key=payload["source_url_key"]).first()
        if duplicate:
            return duplicate
    if payload["name_phone_key"]:
        duplicate = candidates.filter(name_phone_key=payload["name_phone_key"]).first()
        if duplicate:
            return duplicate
    return candidates.filter(
        name__iexact=payload["name"],
        phone=payload["phone"],
        website=payload["website"],
        address=payload["address"],
        city__iexact=payload["city"],
        state=payload["state"],
    ).first()


@dataclass(frozen=True)
class IngestionSummary:
    search_run_id: int
    received: int
    created: int
    duplicates: int
    rejected: int
    total_found: int

    def as_dict(self):
        return {
            "search_run_id": self.search_run_id,
            "received": self.received,
            "created": self.created,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "total_found": self.total_found,
        }


def create_prospecting_campaign(*, form, request):
    actor = _actor_from_request(request)
    with transaction.atomic():
        campaign = form.save(commit=False)
        campaign.created_by = actor
        campaign.full_clean()
        campaign.save()
        form.save_m2m()
        _record_create(
            instance=campaign,
            module="sales_intelligence.campaigns",
            fields=CAMPAIGN_AUDIT_FIELDS,
            request=request,
            actor=actor,
        )
    return campaign


def create_search_run(*, campaign, query, location="", source=SearchRun.Source.GOOGLE_MAPS, requested_limit=None, created_by=None, request=None, start=False):
    actor = created_by or _actor_from_request(request)
    query = normalize_spaces(query)
    location = normalize_spaces(location)
    errors = {}
    if not query:
        errors["query"] = "Informe o termo da pesquisa."
    if len(query) > 180:
        errors["query"] = "Use no máximo 180 caracteres."
    if len(location) > 180:
        errors["location"] = "Use no máximo 180 caracteres."
    _validate_choice("source", source, SearchRun.Source.choices, errors)
    if requested_limit is not None:
        if isinstance(requested_limit, bool) or not isinstance(requested_limit, int) or requested_limit <= 0:
            errors["requested_limit"] = "Informe um limite positivo ou null."
    if campaign.status == ProspectingCampaign.Status.ARCHIVED:
        errors["campaign_id"] = "Campanhas arquivadas não podem iniciar novas pesquisas."
    if errors:
        raise IngestionError(errors)

    with transaction.atomic():
        search_run = SearchRun.objects.create(
            campaign=campaign,
            query=query,
            location=location,
            source=source,
            requested_limit=requested_limit,
            status=SearchRun.Status.RUNNING if start else SearchRun.Status.PENDING,
            started_at=timezone.now() if start else None,
            created_by=actor,
        )
        search_run.full_clean()
        _record_create(instance=search_run, module="sales_intelligence.search_runs", fields=SEARCH_RUN_AUDIT_FIELDS, request=request, actor=actor)
    return search_run


def start_search_run(*, search_run, request=None, started_at=None):
    if search_run.status != SearchRun.Status.PENDING:
        raise ValidationError({"status": "Somente pesquisas pendentes podem iniciar."})
    before = model_snapshot(search_run, SEARCH_RUN_AUDIT_FIELDS)
    with transaction.atomic():
        search_run.status = SearchRun.Status.RUNNING
        search_run.started_at = started_at or timezone.now()
        search_run.full_clean()
        search_run.save(update_fields=["status", "started_at", "updated_at"])
        _record_update(instance=search_run, module="sales_intelligence.search_runs", fields=SEARCH_RUN_AUDIT_FIELDS, before=before, request=request)
    return search_run


def finish_search_run(*, search_run, status=SearchRun.Status.COMPLETED, total_found=None, total_new=None, total_existing=None, total_rejected=None, request=None, finished_at=None, failure_reason=""):
    if status not in FINAL_SEARCH_RUN_STATUSES:
        raise ValidationError({"status": "Informe um status final válido."})
    if status not in _ALLOWED_FINAL_TRANSITIONS.get(search_run.status, set()):
        raise ValidationError({"status": f"Transição inválida a partir de {search_run.status}."})
    reason = normalize_spaces(failure_reason)
    if len(reason) > MAX_FAILURE_REASON_LENGTH:
        raise ValidationError({"reason": f"Use no máximo {MAX_FAILURE_REASON_LENGTH} caracteres."})
    before = model_snapshot(search_run, SEARCH_RUN_AUDIT_FIELDS)
    with transaction.atomic():
        locked = SearchRun.objects.select_for_update().get(pk=search_run.pk)
        if status not in _ALLOWED_FINAL_TRANSITIONS.get(locked.status, set()):
            raise ValidationError({"status": f"Transição inválida a partir de {locked.status}."})
        locked.status = status
        if locked.started_at is None:
            locked.started_at = finished_at or timezone.now()
        locked.finished_at = finished_at or timezone.now()
        locked.failure_reason = reason if status == SearchRun.Status.FAILED else ""
        for field, value in {
            "total_found": total_found,
            "total_new": total_new,
            "total_existing": total_existing,
            "total_rejected": total_rejected,
        }.items():
            if value is not None:
                setattr(locked, field, value)
        _sync_search_run_counters(locked)
        locked.full_clean()
        locked.save()
        _record_update(
            instance=locked,
            module="sales_intelligence.search_runs",
            fields=SEARCH_RUN_AUDIT_FIELDS,
            before=before,
            request=request,
            metadata={"final_status": status, "reason": reason},
        )
    return locked


def ingest_search_results(*, search_run, results, request=None):
    if not isinstance(results, list):
        raise IngestionError({"results": "results precisa ser uma lista."})
    if not results:
        raise IngestionError({"results": "Envie pelo menos um resultado."})
    if len(results) > MAX_BATCH_RESULTS:
        raise IngestionError({"results": f"Envie no máximo {MAX_BATCH_RESULTS} resultados por lote."})

    normalized_results = []
    rejected = 0
    item_errors = []
    for index, item in enumerate(results):
        try:
            normalized_results.append(_normalize_result_payload(item))
        except IngestionError as exc:
            rejected += 1
            item_errors.append({"index": index, "errors": exc.errors})

    if item_errors:
        raise IngestionError({"results": item_errors})

    created = 0
    duplicates = 0
    with transaction.atomic():
        locked_run = SearchRun.objects.select_for_update().get(pk=search_run.pk)
        if locked_run.status != SearchRun.Status.RUNNING:
            raise IngestionConflict({"status": "Resultados só podem ser recebidos em pesquisas RUNNING."})
        before = model_snapshot(locked_run, SEARCH_RUN_AUDIT_FIELDS)
        for payload in normalized_results:
            if _find_duplicate(locked_run, payload):
                duplicates += 1
                continue
            try:
                result = SearchResult(
                    search_run=locked_run,
                    name=payload["name"],
                    phone=payload["phone"],
                    website=payload["website"],
                    address=payload["address"],
                    city=payload["city"],
                    state=payload["state"],
                    source_url=payload["source_url"],
                    source_url_key=payload["source_url_key"],
                    external_id=payload["external_id"],
                    name_phone_key=payload["name_phone_key"],
                    raw_data=payload["raw_data"],
                )
                result.full_clean()
                result.save()
                created += 1
            except IntegrityError:
                duplicates += 1
        _sync_search_run_counters(locked_run)
        locked_run.save(update_fields=["total_found", "total_new", "total_existing", "total_rejected", "updated_at"])
        AuditService.record(
            action=AuditLog.Action.UPDATE,
            module="sales_intelligence.search_runs",
            request=request,
            actor=_actor_from_request(request),
            object_type="SearchRun",
            object_id=locked_run.pk,
            object_repr=str(locked_run),
            before_data=before,
            after_data=model_snapshot(locked_run, SEARCH_RUN_AUDIT_FIELDS),
            metadata={
                "event": "results_ingested",
                "received": len(results),
                "created": created,
                "duplicates": duplicates,
                "rejected": rejected,
            },
        )
    return IngestionSummary(locked_run.pk, len(results), created, duplicates, rejected, locked_run.total_found)


def create_search_result(*, search_run, name, phone="", website="", address="", city="", state="", source_url="", external_id="", raw_data=None, customer=None, processing_status=SearchResult.ProcessingStatus.DISCOVERED):
    payload = _normalize_result_payload({
        "name": name,
        "phone": phone,
        "website": website,
        "address": address,
        "city": city,
        "state": state,
        "source_url": source_url,
        "external_id": external_id,
        "raw_data": raw_data or {},
    })
    with transaction.atomic():
        result = SearchResult.objects.create(
            search_run=search_run,
            name=payload["name"],
            phone=payload["phone"],
            website=payload["website"],
            address=payload["address"],
            city=payload["city"],
            state=payload["state"],
            source_url=payload["source_url"],
            source_url_key=payload["source_url_key"],
            external_id=payload["external_id"],
            name_phone_key=payload["name_phone_key"],
            raw_data=payload["raw_data"],
            customer=customer,
            processing_status=processing_status,
        )
        _record_create(instance=result, module="sales_intelligence.search_results", fields=SEARCH_RESULT_AUDIT_FIELDS)
    return result


def search_run_payload(search_run):
    return {
        "id": search_run.pk,
        "status": search_run.status,
        "query": search_run.query,
        "location": search_run.location,
        "source": search_run.source,
        "requested_limit": search_run.requested_limit,
        "total_found": search_run.total_found,
        "total_new": search_run.total_new,
        "total_existing": search_run.total_existing,
        "total_rejected": search_run.total_rejected,
        "started_at": search_run.started_at.isoformat() if search_run.started_at else None,
        "finished_at": search_run.finished_at.isoformat() if search_run.finished_at else None,
        "failure_reason": search_run.failure_reason,
    }


def search_result_payload(result):
    payload = {
        "id": result.pk,
        "name": result.name,
        "phone": result.phone,
        "website": result.website,
        "address": result.address,
        "city": result.city,
        "state": result.state,
        "source_url": result.source_url,
        "external_id": result.external_id,
        "processing_status": result.processing_status,
        "customer_id": result.customer_id,
    }
    prospect = getattr(result, "campaign_prospect", None)
    if prospect is not None:
        payload["campaign_prospect"] = campaign_prospect_payload(prospect)
    return payload
