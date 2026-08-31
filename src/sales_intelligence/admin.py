from django.contrib import admin

from src.sales_intelligence.models import CampaignProspect
from src.sales_intelligence.models import MarketSegment
from src.sales_intelligence.models import ProspectingCampaign
from src.sales_intelligence.models import SearchResult
from src.sales_intelligence.models import SearchRun


@admin.register(MarketSegment)
class MarketSegmentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProspectingCampaign)
class ProspectingCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "market_segment", "location_description", "status", "created_by", "updated_at")
    list_filter = ("status", "market_segment", "product")
    search_fields = ("name", "objective", "location_description", "product__name", "market_segment__name")
    autocomplete_fields = ("product", "market_segment", "created_by")


class SearchResultInline(admin.TabularInline):
    model = SearchResult
    extra = 0
    fields = ("name", "phone", "website", "city", "state", "processing_status", "customer")
    readonly_fields = ()
    autocomplete_fields = ("customer",)


@admin.register(SearchRun)
class SearchRunAdmin(admin.ModelAdmin):
    list_display = ("campaign", "query", "location", "source", "status", "total_found", "total_new", "total_existing", "total_rejected", "created_by", "created_at")
    list_filter = ("status", "source", "campaign__market_segment")
    search_fields = ("query", "location", "campaign__name")
    autocomplete_fields = ("campaign", "created_by")
    date_hierarchy = "created_at"
    inlines = [SearchResultInline]


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    list_display = ("name", "search_run", "city", "state", "processing_status", "customer", "created_at")
    list_filter = ("processing_status", "state", "search_run__source")
    search_fields = ("name", "phone", "website", "address", "city", "external_id", "customer__legal_name", "customer__trade_name")
    autocomplete_fields = ("search_run", "customer")
    date_hierarchy = "created_at"


@admin.register(CampaignProspect)
class CampaignProspectAdmin(admin.ModelAdmin):
    list_display = ("campaign", "customer", "status", "origin_search_result", "created_by", "created_at")
    list_filter = ("status", "campaign")
    search_fields = ("campaign__name", "customer__legal_name", "customer__trade_name", "origin_search_result__name")
    autocomplete_fields = ("campaign", "customer", "origin_search_result", "created_by")
    date_hierarchy = "created_at"
