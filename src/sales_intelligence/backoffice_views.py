from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from urllib.parse import quote_plus
from django.views.decorators.http import require_POST

from src.backoffice.models import AuditLog
from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.views import backoffice_permission_required
from src.commerce.models import Product
from src.customers.models import Customer
from src.sales_intelligence.forms import ProspectingCampaignForm
from src.sales_intelligence.forms import SearchRunForm
from src.sales_intelligence.models import MarketSegment
from src.sales_intelligence.models import ProspectingCampaign
from src.sales_intelligence.models import SearchResult
from src.sales_intelligence.models import SearchRun
from src.sales_intelligence.services import ConsolidationError
from src.sales_intelligence.services import create_prospecting_campaign
from src.sales_intelligence.services import create_customer_from_search_result
from src.sales_intelligence.services import create_search_run
from src.sales_intelligence.services import finish_search_run
from src.sales_intelligence.services import find_customer_matches
from src.sales_intelligence.services import find_customer_matches_bulk
from src.sales_intelligence.services import link_search_result_to_customer


REVIEW_PAGE_SIZE = 25


def _user_can_manage_sales_intelligence(user):
    from src.backoffice.permissions.services import user_has_backoffice_permission

    return user_has_backoffice_permission(user, BackofficePermission.SALES_INTELLIGENCE_MANAGE)


def _status_badge(status):
    return {
        SearchRun.Status.RUNNING: "bg-primary-subtle text-primary",
        SearchRun.Status.COMPLETED: "bg-success-subtle text-success",
        SearchRun.Status.FAILED: "bg-danger-subtle text-danger",
        SearchRun.Status.CANCELLED: "bg-secondary-subtle text-secondary",
        SearchRun.Status.PENDING: "bg-warning-subtle text-warning",
    }.get(status, "bg-light text-dark")


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_VIEW)
def campaign_list(request):
    campaigns = ProspectingCampaign.objects.select_related("product", "market_segment").annotate(
        search_run_count=Count("search_runs", distinct=True),
    ).order_by("-created_at", "name")
    status = request.GET.get("status", "")
    if status:
        campaigns = campaigns.filter(status=status)
    product_id = request.GET.get("product", "")
    if product_id:
        campaigns = campaigns.filter(product_id=product_id)
    segment_id = request.GET.get("segment", "")
    if segment_id:
        campaigns = campaigns.filter(market_segment_id=segment_id)
    return render(
        request,
        "backoffice/sales_intelligence/campaign_list.html",
        {
            "campaigns": campaigns,
            "statuses": ProspectingCampaign.Status.choices,
            "products": Product.objects.order_by("name"),
            "segments": MarketSegment.objects.order_by("name"),
            "status": status,
            "product_id": product_id,
            "segment_id": segment_id,
            "can_manage": _user_can_manage_sales_intelligence(request.user),
        },
    )


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_MANAGE)
def campaign_create(request):
    form = ProspectingCampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = create_prospecting_campaign(form=form, request=request)
        messages.success(request, "Campanha criada com sucesso.")
        return redirect("backoffice:sales_intelligence_campaign_detail", pk=campaign.pk)
    return render(
        request,
        "backoffice/sales_intelligence/campaign_form.html",
        {"form": form, "title": "Nova campanha"},
    )


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_VIEW)
def campaign_detail(request, pk):
    campaign = get_object_or_404(
        ProspectingCampaign.objects.select_related("product", "market_segment").annotate(
            search_run_count=Count("search_runs", distinct=True),
            result_count=Count("search_runs__results", distinct=True),
            prospect_count=Count("prospects", distinct=True),
        ),
        pk=pk,
    )
    search_runs = campaign.search_runs.order_by("-created_at", "-id")
    return render(
        request,
        "backoffice/sales_intelligence/campaign_detail.html",
        {
            "campaign": campaign,
            "search_runs": search_runs,
            "can_manage": _user_can_manage_sales_intelligence(request.user),
            "status_badges": {run.pk: _status_badge(run.status) for run in search_runs},
        },
    )


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_MANAGE)
def search_run_create(request, campaign_pk):
    campaign = get_object_or_404(ProspectingCampaign, pk=campaign_pk)
    form = SearchRunForm(request.POST or None, initial={"source": SearchRun.Source.GOOGLE_MAPS})
    if request.method == "POST" and form.is_valid():
        search_run = create_search_run(
            campaign=campaign,
            query=form.cleaned_data["query"],
            location=form.cleaned_data["location"],
            source=form.cleaned_data["source"],
            requested_limit=form.cleaned_data["requested_limit"],
            request=request,
            start=True,
        )
        messages.success(request, "Pesquisa criada e iniciada.")
        return redirect("backoffice:sales_intelligence_search_run_page", pk=search_run.pk)
    return render(
        request,
        "backoffice/sales_intelligence/search_run_form.html",
        {"form": form, "campaign": campaign, "title": "Nova pesquisa"},
    )


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_VIEW)
def search_run_list(request):
    search_runs = SearchRun.objects.select_related("campaign", "campaign__product").order_by("-created_at", "-id")
    campaign_id = request.GET.get("campaign", "")
    if campaign_id:
        search_runs = search_runs.filter(campaign_id=campaign_id)
    status = request.GET.get("status", "")
    if status:
        search_runs = search_runs.filter(status=status)
    source = request.GET.get("source", "")
    if source:
        search_runs = search_runs.filter(source=source)
    return render(
        request,
        "backoffice/sales_intelligence/search_run_list.html",
        {
            "search_runs": search_runs,
            "campaigns": ProspectingCampaign.objects.order_by("name"),
            "statuses": SearchRun.Status.choices,
            "sources": SearchRun.Source.choices,
            "campaign_id": campaign_id,
            "status": status,
            "source": source,
        },
    )


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_VIEW)
def search_run_detail(request, pk):
    search_run = get_object_or_404(
        SearchRun.objects.select_related("campaign", "campaign__product", "campaign__market_segment"),
        pk=pk,
    )
    results = search_run.results.select_related("customer").order_by("-created_at", "-id")
    maps_query = " ".join(part for part in [search_run.query, search_run.location] if part).strip()
    return render(
        request,
        "backoffice/sales_intelligence/search_run_detail.html",
        {
            "search_run": search_run,
            "results": results,
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={quote_plus(maps_query)}",
            "can_manage": _user_can_manage_sales_intelligence(request.user),
            "status_badge": _status_badge(search_run.status),
            "can_finish": search_run.status == SearchRun.Status.RUNNING,
            "can_cancel": search_run.status == SearchRun.Status.RUNNING,
        },
    )


@require_POST
@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_MANAGE)
def search_run_complete(request, pk):
    search_run = get_object_or_404(SearchRun, pk=pk)
    try:
        finish_search_run(search_run=search_run, status=SearchRun.Status.COMPLETED, request=request)
        messages.success(request, "Pesquisa finalizada com sucesso.")
    except ValidationError as exc:
        messages.error(request, exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    return redirect("backoffice:sales_intelligence_search_run_page", pk=pk)


@require_POST
@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_MANAGE)
def search_run_cancel(request, pk):
    search_run = get_object_or_404(SearchRun, pk=pk)
    try:
        finish_search_run(search_run=search_run, status=SearchRun.Status.CANCELLED, request=request)
        messages.success(request, "Pesquisa cancelada.")
    except ValidationError as exc:
        messages.error(request, exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    return redirect("backoffice:sales_intelligence_search_run_page", pk=pk)


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_VIEW)
def search_result_review_list(request):
    results = SearchResult.objects.select_related(
        "search_run",
        "search_run__campaign",
        "customer",
    ).order_by("-created_at", "-id")

    campaign_id = request.GET.get("campaign", "")
    if campaign_id:
        results = results.filter(search_run__campaign_id=campaign_id)
    search_run_id = request.GET.get("search_run", "")
    if search_run_id:
        results = results.filter(search_run_id=search_run_id)
    processing_status = request.GET.get("processing_status", "")
    if processing_status:
        results = results.filter(processing_status=processing_status)
    city = request.GET.get("city", "").strip()
    if city:
        results = results.filter(city__icontains=city)
    state = request.GET.get("state", "").strip().upper()
    if state:
        results = results.filter(state=state)
    unconsolidated = request.GET.get("unconsolidated", "")
    if unconsolidated == "1":
        results = results.filter(customer__isnull=True)

    paginator = Paginator(results, REVIEW_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_results = list(page_obj.object_list)
    unconsolidated_results = [result for result in page_results if result.customer_id is None]
    match_map = find_customer_matches_bulk(unconsolidated_results)

    rows = []
    for result in page_results:
        match_result = match_map.get(result.pk)
        rows.append({"result": result, "match_status": match_result.status if match_result else "CONSOLIDATED"})

    filter_params = request.GET.copy()
    filter_params.pop("page", None)
    filter_querystring = filter_params.urlencode()

    return render(
        request,
        "backoffice/sales_intelligence/review_list.html",
        {
            "rows": rows,
            "page_obj": page_obj,
            "filter_querystring": filter_querystring,
            "campaigns": ProspectingCampaign.objects.order_by("name"),
            "search_runs": SearchRun.objects.select_related("campaign").order_by("-created_at")[:100],
            "statuses": SearchResult.ProcessingStatus.choices,
            "campaign_id": campaign_id,
            "search_run_id": search_run_id,
            "processing_status": processing_status,
            "city": city,
            "state": state,
            "unconsolidated": unconsolidated,
        },
    )


@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_VIEW)
def search_result_review_detail(request, pk):
    result = get_object_or_404(
        SearchResult.objects.select_related("search_run", "search_run__campaign", "customer"),
        pk=pk,
    )
    match_result = find_customer_matches(result) if result.customer_id is None else None
    history = AuditLog.objects.filter(module="sales_intelligence.search_results", object_type="SearchResult", object_id=str(result.pk))[:20]
    return render(
        request,
        "backoffice/sales_intelligence/review_detail.html",
        {
            "result": result,
            "match_result": match_result,
            "history": history,
        },
    )


@require_POST
@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_MANAGE)
def search_result_review_link(request, pk, customer_pk):
    result = get_object_or_404(SearchResult, pk=pk)
    customer = get_object_or_404(Customer, pk=customer_pk)
    try:
        link_search_result_to_customer(search_result=result, customer=customer, request=request)
        messages.success(request, "Resultado associado ao cliente existente.")
    except ConsolidationError as exc:
        messages.error(request, str(exc.errors))
    return redirect("backoffice:sales_intelligence_result_detail", pk=pk)


@require_POST
@backoffice_permission_required(BackofficePermission.SALES_INTELLIGENCE_MANAGE)
def search_result_review_create_customer(request, pk):
    result = get_object_or_404(SearchResult, pk=pk)
    try:
        create_customer_from_search_result(search_result=result, request=request)
        messages.success(request, "Customer prospect criado a partir do resultado.")
    except ConsolidationError as exc:
        messages.error(request, str(exc.errors))
    return redirect("backoffice:sales_intelligence_result_detail", pk=pk)
