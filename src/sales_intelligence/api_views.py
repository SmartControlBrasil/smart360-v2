import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods

from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.services import user_has_backoffice_permission
from src.customers.models import Customer
from src.sales_intelligence.models import ProspectingCampaign
from src.sales_intelligence.models import SearchResult
from src.sales_intelligence.models import SearchRun
from src.sales_intelligence.services import ConsolidationConflict
from src.sales_intelligence.services import ConsolidationError
from src.sales_intelligence.services import IngestionError
from src.sales_intelligence.services import campaign_prospect_payload
from src.sales_intelligence.services import create_customer_from_search_result
from src.sales_intelligence.services import create_search_run
from src.sales_intelligence.services import find_customer_matches
from src.sales_intelligence.services import finish_search_run
from src.sales_intelligence.services import ingest_search_results
from src.sales_intelligence.services import link_search_result_to_customer
from src.sales_intelligence.services import search_result_payload
from src.sales_intelligence.services import search_run_payload


def _json_error(errors, status=400):
    return JsonResponse({"errors": errors}, status=status)


def _parse_json_body(request):
    try:
        body = request.body.decode("utf-8") or "{}"
        data = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise IngestionError({"body": "Envie um JSON válido."})
    if not isinstance(data, dict):
        raise IngestionError({"body": "O payload precisa ser um objeto JSON."})
    return data


def _require_sales_intelligence_permission(request, permission):
    if not request.user.is_authenticated:
        return _json_error({"auth": "Autenticação obrigatória."}, status=403)
    if not user_has_backoffice_permission(request.user, permission):
        return _json_error({"permission": "Permissão insuficiente."}, status=403)
    return None


def _validation_errors(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": exc.messages}


def _get_campaign(campaign_id):
    try:
        return ProspectingCampaign.objects.get(pk=campaign_id)
    except ProspectingCampaign.DoesNotExist:
        return None


def _get_search_run(pk):
    try:
        return SearchRun.objects.get(pk=pk)
    except SearchRun.DoesNotExist:
        return None


def _get_search_result(pk):
    try:
        return SearchResult.objects.select_related("search_run__campaign", "customer").get(pk=pk)
    except SearchResult.DoesNotExist:
        return None


def _get_customer(pk):
    try:
        return Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return None


@require_POST
def search_run_create(request):
    denied = _require_sales_intelligence_permission(request, BackofficePermission.SALES_INTELLIGENCE_MANAGE)
    if denied:
        return denied
    try:
        data = _parse_json_body(request)
        campaign_id = data.get("campaign_id")
        if isinstance(campaign_id, bool) or not isinstance(campaign_id, int):
            raise IngestionError({"campaign_id": "Informe um ID de campanha válido."})
        campaign = _get_campaign(campaign_id)
        if campaign is None:
            return _json_error({"campaign_id": "Campanha não encontrada."}, status=404)
        search_run = create_search_run(
            campaign=campaign,
            query=data.get("query", ""),
            location=data.get("location", ""),
            source=data.get("source", SearchRun.Source.GOOGLE_MAPS),
            requested_limit=data.get("requested_limit"),
            request=request,
            start=True,
        )
    except IngestionError as exc:
        return _json_error(exc.errors, status=exc.status_code)
    return JsonResponse(search_run_payload(search_run), status=201)


@require_GET
def search_run_detail(request, pk):
    denied = _require_sales_intelligence_permission(request, BackofficePermission.SALES_INTELLIGENCE_VIEW)
    if denied:
        return denied
    search_run = _get_search_run(pk)
    if search_run is None:
        return _json_error({"search_run_id": "Pesquisa não encontrada."}, status=404)
    return JsonResponse(search_run_payload(search_run))


@require_http_methods(["GET", "POST"])
def search_run_results(request, pk):
    permission = BackofficePermission.SALES_INTELLIGENCE_VIEW if request.method == "GET" else BackofficePermission.SALES_INTELLIGENCE_MANAGE
    denied = _require_sales_intelligence_permission(request, permission)
    if denied:
        return denied
    search_run = _get_search_run(pk)
    if search_run is None:
        return _json_error({"search_run_id": "Pesquisa não encontrada."}, status=404)
    if request.method == "GET":
        results = search_run.results.select_related("customer").order_by("id")
        return JsonResponse({"search_run_id": search_run.pk, "results": [search_result_payload(result) for result in results]})
    try:
        data = _parse_json_body(request)
        summary = ingest_search_results(search_run=search_run, results=data.get("results"), request=request)
    except IngestionError as exc:
        return _json_error(exc.errors, status=exc.status_code)
    return JsonResponse(summary.as_dict())


def _finish_response(request, pk, status):
    denied = _require_sales_intelligence_permission(request, BackofficePermission.SALES_INTELLIGENCE_MANAGE)
    if denied:
        return denied
    search_run = _get_search_run(pk)
    if search_run is None:
        return _json_error({"search_run_id": "Pesquisa não encontrada."}, status=404)
    try:
        data = _parse_json_body(request)
        search_run = finish_search_run(
            search_run=search_run,
            status=status,
            request=request,
            failure_reason=data.get("reason", ""),
        )
    except IngestionError as exc:
        return _json_error(exc.errors, status=exc.status_code)
    except ValidationError as exc:
        return _json_error(_validation_errors(exc), status=409)
    return JsonResponse(search_run_payload(search_run))


@require_POST
def search_run_complete(request, pk):
    return _finish_response(request, pk, SearchRun.Status.COMPLETED)


@require_POST
def search_run_fail(request, pk):
    return _finish_response(request, pk, SearchRun.Status.FAILED)


@require_POST
def search_run_cancel(request, pk):
    return _finish_response(request, pk, SearchRun.Status.CANCELLED)


@require_GET
def search_result_matches(request, pk):
    denied = _require_sales_intelligence_permission(request, BackofficePermission.SALES_INTELLIGENCE_VIEW)
    if denied:
        return denied
    result = _get_search_result(pk)
    if result is None:
        return _json_error({"search_result_id": "Resultado não encontrado."}, status=404)
    payload = find_customer_matches(result).as_dict()
    payload["search_result_id"] = result.pk
    return JsonResponse(payload)


@require_POST
def search_result_link(request, pk):
    denied = _require_sales_intelligence_permission(request, BackofficePermission.SALES_INTELLIGENCE_MANAGE)
    if denied:
        return denied
    result = _get_search_result(pk)
    if result is None:
        return _json_error({"search_result_id": "Resultado não encontrado."}, status=404)
    try:
        data = _parse_json_body(request)
        customer_id = data.get("customer_id")
        if isinstance(customer_id, bool) or not isinstance(customer_id, int):
            raise ConsolidationError({"customer_id": "Informe um ID de cliente válido."})
        customer = _get_customer(customer_id)
        if customer is None:
            return _json_error({"customer_id": "Cliente não encontrado."}, status=404)
        result, prospect = link_search_result_to_customer(search_result=result, customer=customer, request=request)
    except IngestionError as exc:
        return _json_error(exc.errors, status=exc.status_code)
    except ConsolidationError as exc:
        return _json_error(exc.errors, status=exc.status_code)
    return JsonResponse({"result": search_result_payload(result), "campaign_prospect": campaign_prospect_payload(prospect)})


@require_POST
def search_result_create_customer(request, pk):
    denied = _require_sales_intelligence_permission(request, BackofficePermission.SALES_INTELLIGENCE_MANAGE)
    if denied:
        return denied
    result = _get_search_result(pk)
    if result is None:
        return _json_error({"search_result_id": "Resultado não encontrado."}, status=404)
    try:
        customer, result, prospect = create_customer_from_search_result(search_result=result, request=request)
    except ConsolidationError as exc:
        return _json_error(exc.errors, status=exc.status_code)
    return JsonResponse(
        {
            "customer": {"id": customer.pk, "display_name": customer.display_name, "status": customer.status},
            "result": search_result_payload(result),
            "campaign_prospect": campaign_prospect_payload(prospect),
        },
        status=201,
    )
