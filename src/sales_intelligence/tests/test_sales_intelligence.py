import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.backoffice.models import AuditLog
from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.registry import BackofficeRole
from src.backoffice.permissions.services import sync_backoffice_rbac
from src.commerce.models import Brand
from src.commerce.models import Category
from src.commerce.models import Product
from src.customers.models import Customer
from src.sales_intelligence.models import CampaignProspect
from src.sales_intelligence.models import MarketSegment
from src.sales_intelligence.models import ProspectingCampaign
from src.sales_intelligence.models import SearchResult
from src.sales_intelligence.models import SearchRun
from src.sales_intelligence.services import ConsolidationConflict
from src.sales_intelligence.services import create_customer_from_search_result
from src.sales_intelligence.services import create_search_result
from src.sales_intelligence.services import find_customer_matches
from src.sales_intelligence.services import find_customer_matches_bulk
from src.sales_intelligence.services import link_search_result_to_customer
from src.sales_intelligence.services import create_search_run
from src.sales_intelligence.services import finish_search_run
from src.sales_intelligence.services import start_search_run
from src.sales_intelligence.backoffice_views import REVIEW_PAGE_SIZE


class SalesIntelligenceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_backoffice_rbac()
        cls.user_model = get_user_model()

    def user(self, username="commercial", role=BackofficeRole.COMMERCIAL_MANAGER):
        user = self.user_model.objects.create_user(username=username, password="SenhaTeste123!Segura")
        if role is not None:
            user.groups.add(Group.objects.get(name=role.value))
        return user

    def product(self, name="Dune", slug="dune", sku="XY-DUNE"):
        category = Category.objects.create(name="Robôs", slug=f"robos-{slug}")
        brand = Brand.objects.create(name="Xyron Robotics", slug=f"xyron-{slug}")
        return Product.objects.create(name=name, slug=slug, sku=sku, category=category, brand=brand)

    def segment(self, name="Hospital", slug="hospital"):
        return MarketSegment.objects.create(name=name, slug=slug, description="Instituições de saúde")

    def campaign(self):
        return ProspectingCampaign.objects.create(
            name="Dune - Hospitais SP",
            product=self.product(),
            market_segment=self.segment(),
            location_description="Estado de São Paulo",
            objective="Agendar demonstração",
            created_by=self.user(),
        )


class MarketSegmentTests(SalesIntelligenceTestCase):
    def test_creates_market_segment(self):
        segment = self.segment()

        self.assertEqual(str(segment), "Hospital")
        self.assertTrue(segment.is_active)

    def test_market_segment_slug_is_unique(self):
        self.segment()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.segment(name="Hospital privado")


class ProspectingCampaignTests(SalesIntelligenceTestCase):
    def test_creates_campaign_with_product_segment_and_user(self):
        user = self.user("manager")
        product = self.product()
        segment = self.segment()

        campaign = ProspectingCampaign.objects.create(
            name="Dune - Hospitais SP",
            product=product,
            market_segment=segment,
            location_description="São Paulo",
            objective="Agendar demonstração",
            status=ProspectingCampaign.Status.ACTIVE,
            created_by=user,
        )

        self.assertEqual(campaign.product, product)
        self.assertEqual(campaign.market_segment, segment)
        self.assertEqual(campaign.created_by, user)
        self.assertEqual(campaign.status, ProspectingCampaign.Status.ACTIVE)


class SearchRunTests(SalesIntelligenceTestCase):
    def test_creates_search_run_for_campaign(self):
        campaign = self.campaign()
        search_run = create_search_run(campaign=campaign, query="hospital", location="Campinas SP", requested_limit=20)

        self.assertEqual(search_run.campaign, campaign)
        self.assertEqual(search_run.source, SearchRun.Source.GOOGLE_MAPS)
        self.assertEqual(search_run.status, SearchRun.Status.PENDING)
        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.search_runs", object_id=str(search_run.pk)).exists())

    def test_search_run_status_transitions(self):
        search_run = create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP")

        start_search_run(search_run=search_run)
        self.assertEqual(search_run.status, SearchRun.Status.RUNNING)
        self.assertIsNotNone(search_run.started_at)

        create_search_result(search_run=search_run, name="Hospital ABC")
        finished = finish_search_run(search_run=search_run, total_found=10, total_new=7, total_existing=2, total_rejected=1)
        self.assertEqual(finished.status, SearchRun.Status.COMPLETED)
        self.assertEqual(finished.total_found, 1)
        self.assertEqual(finished.total_new, 1)
        self.assertIsNotNone(finished.finished_at)

    def test_running_search_requires_started_at(self):
        search_run = SearchRun(campaign=self.campaign(), query="hospital", status=SearchRun.Status.RUNNING)

        with self.assertRaises(ValidationError):
            search_run.full_clean()

    def test_finished_at_cannot_be_before_started_at(self):
        now = timezone.now()
        search_run = SearchRun(
            campaign=self.campaign(),
            query="hospital",
            status=SearchRun.Status.COMPLETED,
            started_at=now,
            finished_at=now - timezone.timedelta(minutes=1),
        )

        with self.assertRaises(ValidationError):
            search_run.full_clean()


class SearchResultTests(SalesIntelligenceTestCase):
    def test_creates_search_result_preserving_raw_data(self):
        search_run = create_search_run(campaign=self.campaign(), query="hospital")
        result = create_search_result(
            search_run=search_run,
            name="Hospital ABC",
            phone="(11) 9999-9999",
            city="São Paulo",
            state="sp",
            external_id="maps-123",
            raw_data={"rating": 4.7},
        )

        self.assertEqual(result.search_run, search_run)
        self.assertEqual(result.state, "SP")
        self.assertEqual(result.raw_data["rating"], 4.7)
        self.assertIsNone(result.customer)
        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.search_results", object_id=str(result.pk)).exists())

    def test_search_result_can_link_to_customer_without_creating_duplicate_company(self):
        search_run = create_search_run(campaign=self.campaign(), query="hospital")
        customer = Customer.objects.create(legal_name="Hospital ABC", phone="11999999999", city="São Paulo", state="SP")

        result = SearchResult.objects.create(
            search_run=search_run,
            name="Hospital ABC",
            customer=customer,
            processing_status=SearchResult.ProcessingStatus.LINKED,
        )

        self.assertEqual(result.customer, customer)
        self.assertEqual(customer.sales_intelligence_search_results.count(), 1)
        self.assertEqual(Customer.objects.filter(legal_name="Hospital ABC").count(), 1)

    def test_linked_result_requires_customer(self):
        result = SearchResult(
            search_run=create_search_run(campaign=self.campaign(), query="hospital"),
            name="Hospital ABC",
            processing_status=SearchResult.ProcessingStatus.LINKED,
        )

        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_external_id_is_unique_per_search_run_when_present(self):
        search_run = create_search_run(campaign=self.campaign(), query="hospital")
        SearchResult.objects.create(search_run=search_run, name="Hospital ABC", external_id="maps-123")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SearchResult.objects.create(search_run=search_run, name="Hospital ABC duplicado", external_id="maps-123")

    def test_same_external_id_can_appear_in_different_runs(self):
        campaign = self.campaign()
        first = create_search_run(campaign=campaign, query="hospital", location="Campinas")
        second = create_search_run(campaign=campaign, query="hospital particular", location="São Paulo")

        SearchResult.objects.create(search_run=first, name="Hospital ABC", external_id="maps-123")
        SearchResult.objects.create(search_run=second, name="Hospital ABC", external_id="maps-123")

        self.assertEqual(SearchResult.objects.filter(external_id="maps-123").count(), 2)


class SalesIntelligencePermissionTests(SalesIntelligenceTestCase):
    def test_commercial_roles_receive_sales_intelligence_permissions(self):
        manager = self.user("manager", BackofficeRole.COMMERCIAL_MANAGER)
        seller = self.user("seller", BackofficeRole.SALESPERSON)

        self.assertTrue(manager.has_perm("sales_intelligence.view_prospectingcampaign"))
        self.assertTrue(manager.has_perm("sales_intelligence.change_searchresult"))
        self.assertTrue(seller.has_perm("sales_intelligence.view_searchrun"))
        self.assertTrue(seller.has_perm("sales_intelligence.add_searchresult"))

    def test_backoffice_permission_registry_exposes_sales_intelligence(self):
        manager = self.user("registry-manager", BackofficeRole.COMMERCIAL_MANAGER)

        self.assertTrue(manager.has_perm("sales_intelligence.view_marketsegment"))
        self.assertIn(BackofficePermission.SALES_INTELLIGENCE_VIEW, BackofficePermission)


class SalesIntelligenceApiTests(SalesIntelligenceTestCase):
    def post_json(self, name, data, args=None):
        return self.client.post(
            reverse(name, args=args or []),
            data=json.dumps(data),
            content_type="application/json",
        )

    def get_json(self, name, args=None):
        return self.client.get(reverse(name, args=args or []))

    def login(self, username="api-manager", role=BackofficeRole.COMMERCIAL_MANAGER):
        user = self.user(username, role)
        self.client.force_login(user)
        return user

    def running_search_run(self):
        return create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP", start=True)

    def result_payload(self, index=1, **overrides):
        payload = {
            "name": f"Hospital {index}",
            "phone": f"(19) 3333-44{index:02d}",
            "website": f"https://hospital{index}.example.com.br",
            "address": f"Rua {index}, 123",
            "city": "Campinas",
            "state": "SP",
            "source_url": f"https://www.google.com/maps/place/hospital-{index}/",
            "external_id": f"maps-{index}",
            "raw_data": {"category": "Hospital", "rank": index},
        }
        payload.update(overrides)
        return payload

    def test_authorized_search_run_creation_starts_running(self):
        user = self.login()
        campaign = self.campaign()

        response = self.post_json("backoffice:sales_intelligence_search_run_create", {
            "campaign_id": campaign.pk,
            "query": " hospital ",
            "location": "Campinas SP",
            "source": SearchRun.Source.GOOGLE_MAPS,
            "requested_limit": 100,
        })

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], SearchRun.Status.RUNNING)
        self.assertEqual(data["query"], "hospital")
        self.assertEqual(data["requested_limit"], 100)
        self.assertIsNotNone(data["started_at"])
        self.assertTrue(SearchRun.objects.filter(pk=data["id"], created_by=user).exists())

    def test_search_run_creation_without_permission_is_forbidden(self):
        self.login("no-role", role=None)
        campaign = self.campaign()

        response = self.post_json("backoffice:sales_intelligence_search_run_create", {"campaign_id": campaign.pk, "query": "hospital"})

        self.assertEqual(response.status_code, 403)

    def test_search_run_creation_with_missing_campaign_returns_404(self):
        self.login()

        response = self.post_json("backoffice:sales_intelligence_search_run_create", {"campaign_id": 999999, "query": "hospital"})

        self.assertEqual(response.status_code, 404)
        self.assertIn("campaign_id", response.json()["errors"])

    def test_search_run_creation_rejects_invalid_payload(self):
        self.login()
        campaign = self.campaign()

        response = self.post_json("backoffice:sales_intelligence_search_run_create", {
            "campaign_id": campaign.pk,
            "query": "",
            "source": "INVALID",
            "requested_limit": -1,
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("query", response.json()["errors"])
        self.assertIn("source", response.json()["errors"])
        self.assertIn("requested_limit", response.json()["errors"])

    def test_archived_campaign_cannot_start_search_run(self):
        self.login()
        campaign = self.campaign()
        campaign.status = ProspectingCampaign.Status.ARCHIVED
        campaign.save(update_fields=["status", "updated_at"])

        response = self.post_json("backoffice:sales_intelligence_search_run_create", {"campaign_id": campaign.pk, "query": "hospital"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("campaign_id", response.json()["errors"])

    def test_ingests_single_result(self):
        self.login()
        search_run = self.running_search_run()

        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload()]}, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 1)
        self.assertEqual(SearchResult.objects.count(), 1)
        search_run.refresh_from_db()
        self.assertEqual(search_run.total_found, 1)
        self.assertEqual(search_run.total_new, 1)
        self.assertEqual(search_run.total_existing, 0)

    def test_ingests_batch_results(self):
        self.login()
        search_run = self.running_search_run()

        response = self.post_json("backoffice:sales_intelligence_search_run_results", {
            "results": [self.result_payload(1), self.result_payload(2), self.result_payload(3)]
        }, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["received"], 3)
        self.assertEqual(response.json()["created"], 3)
        self.assertEqual(response.json()["duplicates"], 0)
        self.assertEqual(SearchResult.objects.count(), 3)

    def test_reposting_same_batch_is_idempotent(self):
        self.login()
        search_run = self.running_search_run()
        batch = [self.result_payload(index) for index in range(1, 11)]

        first = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": batch}, [search_run.pk])
        second = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": batch}, [search_run.pk])

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["created"], 10)
        self.assertEqual(second.json()["created"], 0)
        self.assertEqual(second.json()["duplicates"], 10)
        self.assertEqual(SearchResult.objects.filter(search_run=search_run).count(), 10)
        search_run.refresh_from_db()
        self.assertEqual(search_run.total_found, 10)

    def test_external_id_duplicate_is_idempotent(self):
        self.login()
        search_run = self.running_search_run()
        first = self.result_payload(1, source_url="https://www.google.com/maps/place/a/")
        duplicate = self.result_payload(2, external_id="maps-1", source_url="https://www.google.com/maps/place/b/")

        self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [first]}, [search_run.pk])
        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [duplicate]}, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["duplicates"], 1)
        self.assertEqual(SearchResult.objects.filter(search_run=search_run).count(), 1)

    def test_name_phone_duplicate_is_idempotent_without_external_id(self):
        self.login()
        search_run = self.running_search_run()
        first = self.result_payload(1, external_id="", source_url="", name=" Hospital ABC ", phone="+55 19 3333-4444")
        duplicate = self.result_payload(2, external_id="", source_url="", name="Hospital   ABC", phone="19 3333 4444")

        self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [first]}, [search_run.pk])
        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [duplicate]}, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["duplicates"], 1)
        self.assertEqual(SearchResult.objects.filter(search_run=search_run).count(), 1)

    def test_missing_search_run_returns_404(self):
        self.login()

        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload()]}, [999999])

        self.assertEqual(response.status_code, 404)

    def test_ingestion_after_completed_is_blocked(self):
        self.login()
        search_run = self.running_search_run()
        finish_search_run(search_run=search_run)

        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload()]}, [search_run.pk])

        self.assertEqual(response.status_code, 409)
        self.assertEqual(SearchResult.objects.count(), 0)

    def test_complete_endpoint(self):
        self.login()
        search_run = self.running_search_run()

        response = self.post_json("backoffice:sales_intelligence_search_run_complete", {}, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], SearchRun.Status.COMPLETED)
        self.assertIsNotNone(response.json()["finished_at"])
        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.search_runs", object_id=str(search_run.pk), metadata__final_status=SearchRun.Status.COMPLETED).exists())

    def test_cancel_endpoint(self):
        self.login()
        search_run = self.running_search_run()

        response = self.post_json("backoffice:sales_intelligence_search_run_cancel", {}, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], SearchRun.Status.CANCELLED)

    def test_fail_endpoint_records_reason(self):
        self.login()
        search_run = self.running_search_run()

        response = self.post_json("backoffice:sales_intelligence_search_run_fail", {"reason": "Google Maps deixou de responder"}, [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], SearchRun.Status.FAILED)
        self.assertEqual(response.json()["failure_reason"], "Google Maps deixou de responder")

    def test_invalid_transition_is_blocked(self):
        self.login()
        search_run = self.running_search_run()
        self.post_json("backoffice:sales_intelligence_search_run_complete", {}, [search_run.pk])

        response = self.post_json("backoffice:sales_intelligence_search_run_cancel", {}, [search_run.pk])

        self.assertEqual(response.status_code, 409)

    def test_status_endpoint(self):
        self.login()
        search_run = self.running_search_run()

        response = self.get_json("backoffice:sales_intelligence_search_run_detail", [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], search_run.pk)
        self.assertEqual(response.json()["status"], SearchRun.Status.RUNNING)

    def test_results_listing_endpoint(self):
        self.login()
        search_run = self.running_search_run()
        customer = Customer.objects.create(legal_name="Hospital ABC")
        result = SearchResult.objects.create(search_run=search_run, name="Hospital ABC", customer=customer, processing_status=SearchResult.ProcessingStatus.LINKED)

        response = self.get_json("backoffice:sales_intelligence_search_run_results", [search_run.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["id"], result.pk)
        self.assertEqual(response.json()["results"][0]["customer_id"], customer.pk)

    def test_counters_after_multiple_batches(self):
        self.login()
        search_run = self.running_search_run()

        self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload(1), self.result_payload(2)]}, [search_run.pk])
        self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload(2), self.result_payload(3)]}, [search_run.pk])

        search_run.refresh_from_db()
        self.assertEqual(search_run.total_found, 3)
        self.assertEqual(search_run.total_new, 3)
        self.assertEqual(search_run.total_existing, 0)
        self.assertEqual(search_run.total_rejected, 0)

    def test_raw_data_is_preserved_and_customer_remains_null(self):
        self.login()
        search_run = self.running_search_run()
        raw_data = {"category": "Hospital", "nested": {"value": "original"}}

        self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload(raw_data=raw_data)]}, [search_run.pk])

        result = SearchResult.objects.get()
        self.assertEqual(result.raw_data, raw_data)
        self.assertIsNone(result.customer)

    def test_salesperson_role_is_authorized(self):
        self.login("api-seller", BackofficeRole.SALESPERSON)
        campaign = self.campaign()

        response = self.post_json("backoffice:sales_intelligence_search_run_create", {"campaign_id": campaign.pk, "query": "hospital"})

        self.assertEqual(response.status_code, 201)

    def test_user_without_role_is_blocked(self):
        self.login("api-user-without-role", role=None)
        search_run = self.running_search_run()

        response = self.get_json("backoffice:sales_intelligence_search_run_detail", [search_run.pk])

        self.assertEqual(response.status_code, 403)

    def test_results_payload_must_be_array_and_not_empty(self):
        self.login()
        search_run = self.running_search_run()

        not_array = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": {}}, [search_run.pk])
        empty = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": []}, [search_run.pk])

        self.assertEqual(not_array.status_code, 400)
        self.assertEqual(empty.status_code, 400)

    def test_result_name_is_required(self):
        self.login()
        search_run = self.running_search_run()

        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": [self.result_payload(name="   ")]}, [search_run.pk])

        self.assertEqual(response.status_code, 400)
        self.assertIn("results", response.json()["errors"])

    def test_batch_size_limit(self):
        self.login()
        search_run = self.running_search_run()
        payload = [self.result_payload(index, external_id=f"maps-limit-{index}", source_url=f"https://example.com/{index}") for index in range(101)]

        response = self.post_json("backoffice:sales_intelligence_search_run_results", {"results": payload}, [search_run.pk])

        self.assertEqual(response.status_code, 400)
        self.assertIn("100", response.json()["errors"]["results"])



class SalesIntelligenceConsolidationTests(SalesIntelligenceTestCase):
    def search_result(self, **overrides):
        data = {
            "search_run": create_search_run(campaign=self.campaign(), query="hospital"),
            "name": "Hospital ABC",
            "phone": "+55 (19) 3333-4444",
            "website": "https://www.hospitalabc.com.br/unidade",
            "address": "Rua Um, 123",
            "city": "Campinas",
            "state": "SP",
        }
        data.update(overrides)
        return SearchResult.objects.create(**data)

    def customer(self, **overrides):
        data = {
            "legal_name": "Hospital ABC",
            "trade_name": "Hospital ABC",
            "phone": "(19) 3333-4444",
            "website": "https://hospitalabc.com.br",
            "status": Customer.Status.ACTIVE,
        }
        data.update(overrides)
        return Customer.objects.create(**data)

    def test_phone_match_is_exact_even_with_masks(self):
        result = self.search_result(website="")
        customer = self.customer(website="")

        match = find_customer_matches(result)

        self.assertEqual(match.status, "EXACT_MATCH")
        self.assertEqual(match.candidates[0].customer, customer)
        self.assertIn("PHONE", match.candidates[0].reasons)

    def test_website_domain_match_is_exact(self):
        result = self.search_result(phone="")
        customer = self.customer(phone="", website="https://hospitalabc.com.br/contato")

        match = find_customer_matches(result)

        self.assertEqual(match.status, "EXACT_MATCH")
        self.assertEqual(match.candidates[0].customer, customer)
        self.assertIn("WEBSITE_DOMAIN", match.candidates[0].reasons)

    def test_name_alone_does_not_match(self):
        result = self.search_result(phone="", website="")
        self.customer(phone="", website="")

        match = find_customer_matches(result)

        self.assertEqual(match.status, "NO_MATCH")
        self.assertEqual(match.candidates, tuple())

    def test_multiple_customers_with_same_signal_are_ambiguous(self):
        result = self.search_result(website="")
        self.customer(legal_name="Hospital ABC Matriz", website="")
        self.customer(legal_name="Hospital ABC Filial", trade_name="Hospital ABC Filial", website="")

        match = find_customer_matches(result)

        self.assertEqual(match.status, "AMBIGUOUS")
        self.assertEqual(len(match.candidates), 2)

    def test_unique_phone_and_domain_pointing_to_same_customer_is_exact(self):
        result = self.search_result()
        customer = self.customer()

        match = find_customer_matches(result)

        self.assertEqual(match.status, "EXACT_MATCH")
        self.assertEqual(match.candidates[0].customer, customer)
        self.assertIn("PHONE", match.candidates[0].reasons)
        self.assertIn("WEBSITE_DOMAIN", match.candidates[0].reasons)

    def test_phone_and_domain_pointing_to_different_customers_are_ambiguous(self):
        result = self.search_result()
        self.customer(legal_name="Por telefone", website="")
        self.customer(
            legal_name="Por dominio",
            trade_name="Por dominio",
            phone="",
            website="https://hospitalabc.com.br",
        )

        match = find_customer_matches(result)

        self.assertEqual(match.status, "AMBIGUOUS")
        self.assertEqual(len(match.candidates), 2)

    def test_duplicate_domain_is_ambiguous(self):
        result = self.search_result(phone="")
        self.customer(legal_name="Unidade 1", phone="", website="https://hospitalabc.com.br")
        self.customer(legal_name="Unidade 2", trade_name="Unidade 2", phone="", website="http://www.hospitalabc.com.br/x")

        match = find_customer_matches(result)

        self.assertEqual(match.status, "AMBIGUOUS")
        self.assertEqual(len(match.candidates), 2)

    def test_no_phone_or_domain_is_no_match(self):
        result = self.search_result(phone="", website="")
        self.customer()

        match = find_customer_matches(result)

        self.assertEqual(match.status, "NO_MATCH")

    def test_identical_name_with_different_identifiers_does_not_match(self):
        result = self.search_result(phone="11911112222", website="https://outra.com.br")
        self.customer()

        match = find_customer_matches(result)

        self.assertEqual(match.status, "NO_MATCH")

    def test_whatsapp_can_match_when_phone_field_is_empty(self):
        result = self.search_result(website="")
        customer = self.customer(phone="", website="", whatsapp="(19) 3333-4444")

        match = find_customer_matches(result)

        self.assertEqual(match.status, "EXACT_MATCH")
        self.assertEqual(match.candidates[0].customer, customer)
        self.assertIn("PHONE", match.candidates[0].reasons)

    def test_create_customer_from_result_persists_normalized_fields(self):
        result = self.search_result()

        customer, _, _ = create_customer_from_search_result(search_result=result)

        self.assertEqual(customer.normalized_phone, "1933334444")
        self.assertEqual(customer.normalized_domain, "hospitalabc.com.br")

    def test_linking_existing_customer_creates_campaign_prospect(self):
        result = self.search_result()
        customer = self.customer()

        linked_result, prospect = link_search_result_to_customer(search_result=result, customer=customer)

        self.assertEqual(linked_result.customer_id, customer.pk)
        self.assertEqual(linked_result.processing_status, SearchResult.ProcessingStatus.LINKED)
        self.assertEqual(prospect.customer_id, customer.pk)
        self.assertEqual(CampaignProspect.objects.count(), 1)

    def test_linking_same_customer_is_idempotent(self):
        result = self.search_result()
        customer = self.customer()

        link_search_result_to_customer(search_result=result, customer=customer)
        link_search_result_to_customer(search_result=result, customer=customer)

        self.assertEqual(CampaignProspect.objects.filter(campaign=result.search_run.campaign, customer=customer).count(), 1)

    def test_linking_different_customer_after_consolidation_conflicts(self):
        result = self.search_result()
        first = self.customer()
        second = self.customer(legal_name="Hospital XYZ", trade_name="Hospital XYZ", phone="11999999999", website="https://xyz.example.com")

        link_search_result_to_customer(search_result=result, customer=first)

        with self.assertRaises(ConsolidationConflict):
            link_search_result_to_customer(search_result=result, customer=second)

    def test_create_customer_from_result_sets_prospect_without_document_or_email(self):
        user = self.user("creator")
        result = self.search_result()

        customer, updated_result, prospect = create_customer_from_search_result(search_result=result, actor=user)

        self.assertEqual(customer.status, Customer.Status.PROSPECT)
        self.assertEqual(customer.trade_name, result.name)
        self.assertEqual(customer.legal_name, result.name)
        self.assertIsNone(customer.document)
        self.assertEqual(customer.email, "")
        self.assertEqual(updated_result.processing_status, SearchResult.ProcessingStatus.CREATED)
        self.assertEqual(prospect.customer_id, customer.pk)

    def test_create_customer_from_result_is_idempotent(self):
        result = self.search_result()

        first_customer, _, first_prospect = create_customer_from_search_result(search_result=result)
        second_customer, _, second_prospect = create_customer_from_search_result(search_result=result)

        self.assertEqual(first_customer.pk, second_customer.pk)
        self.assertEqual(first_prospect.pk, second_prospect.pk)
        self.assertEqual(Customer.objects.filter(legal_name=result.name).count(), 1)

    def test_create_customer_is_blocked_when_result_is_linked_to_existing(self):
        result = self.search_result()
        customer = self.customer()
        link_search_result_to_customer(search_result=result, customer=customer)

        with self.assertRaises(ConsolidationConflict):
            create_customer_from_search_result(search_result=result)

    def test_same_customer_in_campaign_gets_single_campaign_prospect(self):
        campaign = self.campaign()
        run = create_search_run(campaign=campaign, query="hospital")
        customer = self.customer()
        first = SearchResult.objects.create(search_run=run, name="Hospital ABC")
        second = SearchResult.objects.create(search_run=run, name="Hospital ABC unidade 2")

        link_search_result_to_customer(search_result=first, customer=customer)
        link_search_result_to_customer(search_result=second, customer=customer)

        self.assertEqual(CampaignProspect.objects.filter(campaign=campaign, customer=customer).count(), 1)

    def test_counters_separate_existing_linked_from_created_prospect(self):
        campaign = self.campaign()
        run = create_search_run(campaign=campaign, query="hospital")
        linked = SearchResult.objects.create(search_run=run, name="Hospital ABC")
        created = SearchResult.objects.create(search_run=run, name="Hospital Novo")
        customer = self.customer()

        link_search_result_to_customer(search_result=linked, customer=customer)
        create_customer_from_search_result(search_result=created)
        run.refresh_from_db()

        self.assertEqual(run.total_found, 2)
        self.assertEqual(run.total_existing, 1)
        self.assertEqual(run.total_new, 1)

    def test_consolidation_records_audit_entries(self):
        result = self.search_result()
        customer = self.customer()

        link_search_result_to_customer(search_result=result, customer=customer)

        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.search_results", metadata__event="customer_linked").exists())
        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.campaign_prospects", object_type="CampaignProspect").exists())


class SalesIntelligenceBulkMatchTests(SalesIntelligenceTestCase):
    def _search_run(self):
        return create_search_run(campaign=self.campaign(), query="hospital", start=True)

    def test_bulk_match_covers_mixed_page_and_does_not_scan_per_result(self):
        search_run = self._search_run()
        unique_phone_customer = Customer.objects.create(
            legal_name="Unico Telefone",
            phone="11910000001",
            website="",
        )
        unique_domain_customer = Customer.objects.create(
            legal_name="Unico Dominio",
            phone="",
            website="https://www.clinicaunica.com.br/sobre",
        )
        shared_phone_a = Customer.objects.create(legal_name="Compartilhado A", phone="11920000000", website="")
        shared_phone_b = Customer.objects.create(legal_name="Compartilhado B", phone="11920000000", website="")
        conflict_phone = Customer.objects.create(legal_name="Conflito Phone", phone="11930000000", website="")
        conflict_domain = Customer.objects.create(
            legal_name="Conflito Domain",
            phone="",
            website="https://conflito.com.br",
        )
        name_only_customer = Customer.objects.create(
            legal_name="Hospital Homônimo",
            phone="11940000000",
            website="https://homonimo.com.br",
        )
        for index in range(100):
            Customer.objects.create(
                legal_name=f"Ruido {index}",
                phone=f"1188{index:07d}",
                website=f"https://ruido{index}.example.com",
            )

        results = [
            SearchResult.objects.create(search_run=search_run, name="Lead phone", phone="(11) 91000-0001", website=""),
            SearchResult.objects.create(
                search_run=search_run,
                name="Lead domain",
                phone="",
                website="http://clinicaunica.com.br/contato?utm=1",
            ),
            SearchResult.objects.create(search_run=search_run, name="Lead duplicate phone", phone="11920000000", website=""),
            SearchResult.objects.create(
                search_run=search_run,
                name="Lead conflict",
                phone="11930000000",
                website="https://www.conflito.com.br/x",
            ),
            SearchResult.objects.create(search_run=search_run, name="Hospital Homônimo", phone="", website=""),
            SearchResult.objects.create(
                search_run=search_run,
                name="Hospital Homônimo",
                phone="11950000000",
                website="https://outrohomonimo.com.br",
            ),
        ]
        for index in range(44):
            results.append(
                SearchResult.objects.create(
                    search_run=search_run,
                    name=f"Lead extra {index}",
                    phone=f"1177{index:07d}",
                    website="",
                )
            )

        self.assertGreaterEqual(Customer.objects.count(), 100)
        self.assertGreaterEqual(len(results), 50)

        with self.assertNumQueries(1):
            matches = find_customer_matches_bulk(results)

        self.assertEqual(len(matches), len(results))
        self.assertEqual(matches[results[0].pk].status, "EXACT_MATCH")
        self.assertEqual(matches[results[0].pk].candidates[0].customer, unique_phone_customer)
        self.assertEqual(matches[results[1].pk].status, "EXACT_MATCH")
        self.assertEqual(matches[results[1].pk].candidates[0].customer, unique_domain_customer)
        self.assertEqual(matches[results[2].pk].status, "AMBIGUOUS")
        self.assertEqual(
            {candidate.customer for candidate in matches[results[2].pk].candidates},
            {shared_phone_a, shared_phone_b},
        )
        self.assertEqual(matches[results[3].pk].status, "AMBIGUOUS")
        self.assertEqual(
            {candidate.customer for candidate in matches[results[3].pk].candidates},
            {conflict_phone, conflict_domain},
        )
        self.assertEqual(matches[results[4].pk].status, "NO_MATCH")
        self.assertEqual(matches[results[5].pk].status, "NO_MATCH")
        self.assertEqual(matches[results[6].pk].status, "NO_MATCH")
        self.assertNotIn(name_only_customer, [candidate.customer for match in matches.values() for candidate in match.candidates])

    def test_find_customer_matches_uses_bulk_indexed_path(self):
        search_run = self._search_run()
        result = SearchResult.objects.create(search_run=search_run, name="Hospital ABC", phone="1933334444", website="")
        customer = Customer.objects.create(legal_name="Hospital ABC", phone="(19) 3333-4444", website="")

        with self.assertNumQueries(1):
            match = find_customer_matches(result)

        self.assertEqual(match.status, "EXACT_MATCH")
        self.assertEqual(match.candidates[0].customer, customer)


class SalesIntelligenceConsolidationApiTests(SalesIntelligenceTestCase):
    def post_json(self, name, data, args=None):
        return self.client.post(
            reverse(name, args=args or []),
            data=json.dumps(data),
            content_type="application/json",
        )

    def get_json(self, name, args=None):
        return self.client.get(reverse(name, args=args or []))

    def login(self, username="consolidation-api-manager", role=BackofficeRole.COMMERCIAL_MANAGER):
        user = self.user(username, role)
        self.client.force_login(user)
        return user

    def running_search_run(self):
        return create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP", start=True)

    def stored_result(self):
        search_run = self.running_search_run()
        return SearchResult.objects.create(
            search_run=search_run,
            name="Hospital ABC",
            phone="(19) 3333-4444",
            website="https://hospitalabc.com.br",
            city="Campinas",
            state="SP",
        )

    def test_matches_endpoint_returns_exact_candidate(self):
        self.login()
        result = self.stored_result()
        customer = Customer.objects.create(legal_name="Hospital ABC", phone="1933334444")

        response = self.get_json("backoffice:sales_intelligence_search_result_matches", [result.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "EXACT_MATCH")
        self.assertEqual(response.json()["candidates"][0]["customer_id"], customer.pk)

    def test_matches_endpoint_without_permission_is_forbidden(self):
        self.login("blocked-matches", role=None)
        result = self.stored_result()

        response = self.get_json("backoffice:sales_intelligence_search_result_matches", [result.pk])

        self.assertEqual(response.status_code, 403)

    def test_link_endpoint_links_existing_customer(self):
        self.login()
        result = self.stored_result()
        customer = Customer.objects.create(legal_name="Hospital ABC", phone="1933334444")

        response = self.post_json("backoffice:sales_intelligence_search_result_link", {"customer_id": customer.pk}, [result.pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["customer_id"], customer.pk)
        self.assertEqual(response.json()["campaign_prospect"]["customer_id"], customer.pk)

    def test_link_endpoint_rejects_invalid_customer_id(self):
        self.login()
        result = self.stored_result()

        response = self.post_json("backoffice:sales_intelligence_search_result_link", {"customer_id": "abc"}, [result.pk])

        self.assertEqual(response.status_code, 400)

    def test_link_endpoint_conflicts_after_different_consolidation(self):
        self.login()
        result = self.stored_result()
        first = Customer.objects.create(legal_name="Hospital ABC", phone="1933334444")
        second = Customer.objects.create(legal_name="Hospital XYZ", phone="1199999999")
        link_search_result_to_customer(search_result=result, customer=first)

        response = self.post_json("backoffice:sales_intelligence_search_result_link", {"customer_id": second.pk}, [result.pk])

        self.assertEqual(response.status_code, 409)

    def test_create_customer_endpoint_creates_prospect_customer(self):
        self.login()
        result = self.stored_result()

        response = self.post_json("backoffice:sales_intelligence_search_result_create_customer", {}, [result.pk])

        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(pk=response.json()["customer"]["id"])
        self.assertEqual(customer.status, Customer.Status.PROSPECT)
        self.assertIsNone(customer.document)
        self.assertEqual(customer.email, "")

    def test_create_customer_endpoint_is_idempotent_for_same_result(self):
        self.login()
        result = self.stored_result()

        first = self.post_json("backoffice:sales_intelligence_search_result_create_customer", {}, [result.pk])
        second = self.post_json("backoffice:sales_intelligence_search_result_create_customer", {}, [result.pk])

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["customer"]["id"], second.json()["customer"]["id"])
        self.assertEqual(CampaignProspect.objects.count(), 1)

    def test_create_customer_endpoint_without_permission_is_forbidden(self):
        self.login("blocked-create", role=None)
        result = self.stored_result()

        response = self.post_json("backoffice:sales_intelligence_search_result_create_customer", {}, [result.pk])

        self.assertEqual(response.status_code, 403)

    def test_review_list_page_renders_filters_and_actions(self):
        self.login()
        result = self.stored_result()

        response = self.client.get(reverse("backoffice:sales_intelligence_review"), {"unconsolidated": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, result.name)
        self.assertContains(response, "Abrir")

    def test_review_list_paginates_and_preserves_filters(self):
        self.login()
        search_run = self.running_search_run()
        for index in range(REVIEW_PAGE_SIZE + 3):
            SearchResult.objects.create(
                search_run=search_run,
                name=f"Lead paginado {index:02d}",
                city="Campinas",
                state="SP",
            )

        page_one = self.client.get(
            reverse("backoffice:sales_intelligence_review"),
            {"unconsolidated": "1", "city": "Campinas"},
        )
        page_two = self.client.get(
            reverse("backoffice:sales_intelligence_review"),
            {"unconsolidated": "1", "city": "Campinas", "page": "2"},
        )

        self.assertEqual(page_one.status_code, 200)
        self.assertEqual(page_two.status_code, 200)
        self.assertEqual(len(page_one.context["rows"]), REVIEW_PAGE_SIZE)
        self.assertEqual(len(page_two.context["rows"]), 3)
        self.assertContains(page_one, "unconsolidated=1")
        self.assertContains(page_one, "city=Campinas")
        self.assertContains(page_one, "page=2")
        self.assertContains(page_two, "Lead paginado")

    def test_review_detail_page_renders_candidate_and_create_action(self):
        self.login()
        result = self.stored_result()
        Customer.objects.create(legal_name="Hospital ABC", phone="1933334444")

        response = self.client.get(reverse("backoffice:sales_intelligence_result_detail", args=[result.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Associar")
        self.assertContains(response, "Novo Customer prospect")

    def test_review_detail_for_consolidated_result_hides_create_action(self):
        self.login()
        result = self.stored_result()
        customer = Customer.objects.create(legal_name="Hospital ABC", phone="1933334444")
        link_search_result_to_customer(search_result=result, customer=customer)

        response = self.client.get(reverse("backoffice:sales_intelligence_result_detail", args=[result.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Consolidado com")
        self.assertNotContains(response, "Novo Customer prospect")



class SalesIntelligenceBackofficeOperationalTests(SalesIntelligenceTestCase):
    def login(self, username="ops-manager", role=BackofficeRole.COMMERCIAL_MANAGER):
        user = self.user(username, role)
        self.client.force_login(user)
        return user

    def campaign_payload(self, product=None, segment=None, **overrides):
        product = product or self.product(name="Dune", slug="dune-ops", sku="XY-DUNE-OPS")
        segment = segment or self.segment(name="Hospital", slug="hospital-ops")
        payload = {
            "name": "Dune — Hospitais SP",
            "product": product.pk,
            "market_segment": segment.pk,
            "location_description": "São Paulo",
            "objective": "Agendar demonstração",
            "status": ProspectingCampaign.Status.ACTIVE,
        }
        payload.update(overrides)
        return payload

    def search_run_payload(self, **overrides):
        payload = {
            "query": "hospital",
            "location": "Campinas SP",
            "source": SearchRun.Source.GOOGLE_MAPS,
            "requested_limit": 100,
        }
        payload.update(overrides)
        return payload

    def test_menu_appears_for_authorized_user(self):
        self.login("menu-authorized")
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertContains(response, "Prospecção")
        self.assertContains(response, "Campanhas")
        self.assertContains(response, "Pesquisas")
        self.assertContains(response, "Revisão")

    def test_menu_does_not_appear_without_permission(self):
        self.login("menu-viewer", BackofficeRole.VIEWER)
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertNotContains(response, "Prospecção")
        self.assertNotContains(response, "Campanhas")

    def test_campaign_list_renders_campaigns(self):
        self.login("campaign-list")
        campaign = self.campaign()
        response = self.client.get(reverse("backoffice:sales_intelligence_campaign_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, campaign.name)
        self.assertContains(response, "Abrir")

    def test_campaign_create_form_creates_campaign(self):
        user = self.login("campaign-create")
        payload = self.campaign_payload()
        response = self.client.post(reverse("backoffice:sales_intelligence_campaign_create"), payload)
        campaign = ProspectingCampaign.objects.get(name="Dune — Hospitais SP")
        self.assertRedirects(response, reverse("backoffice:sales_intelligence_campaign_detail", args=[campaign.pk]))
        self.assertEqual(campaign.created_by, user)
        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.campaigns", object_id=str(campaign.pk)).exists())

    def test_user_without_manage_cannot_create_campaign(self):
        self.login("campaign-no-manage", BackofficeRole.VIEWER)
        response = self.client.get(reverse("backoffice:sales_intelligence_campaign_create"))
        self.assertEqual(response.status_code, 403)

    def test_campaign_detail_shows_metrics_and_new_search_button(self):
        self.login("campaign-detail")
        campaign = self.campaign()
        create_search_run(campaign=campaign, query="hospital", location="Campinas SP", start=True)
        response = self.client.get(reverse("backoffice:sales_intelligence_campaign_detail", args=[campaign.pk]))
        self.assertContains(response, campaign.name)
        self.assertContains(response, "Métricas")
        self.assertContains(response, "Nova pesquisa")

    def test_search_run_create_form_creates_running_search_run(self):
        user = self.login("run-create")
        campaign = self.campaign()
        response = self.client.post(reverse("backoffice:sales_intelligence_search_run_create_form", args=[campaign.pk]), self.search_run_payload())
        search_run = SearchRun.objects.get(campaign=campaign, query="hospital")
        self.assertRedirects(response, reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertEqual(search_run.status, SearchRun.Status.RUNNING)
        self.assertIsNotNone(search_run.started_at)
        self.assertEqual(search_run.created_by, user)

    def test_search_run_create_form_uses_campaign_from_url(self):
        self.login("run-campaign")
        campaign = self.campaign()
        self.client.post(reverse("backoffice:sales_intelligence_search_run_create_form", args=[campaign.pk]), self.search_run_payload())
        self.assertEqual(SearchRun.objects.get(query="hospital").campaign, campaign)

    def test_search_run_detail_shows_extension_id(self):
        self.login("run-detail-id")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP", start=True)
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertContains(response, f"SearchRun #{search_run.pk}")
        self.assertContains(response, "ID para extensão Chrome")
        self.assertContains(response, f'id="search-run-id-value">{search_run.pk}</div>', html=False)

    def test_google_maps_link_contains_encoded_query_and_location(self):
        self.login("run-maps")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP", start=True)
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertContains(response, "https://www.google.com/maps/search/?api=1&amp;query=hospital+Campinas+SP")

    def test_search_run_list_renders_recent_runs(self):
        self.login("run-list")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP", start=True)
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_list"))
        self.assertContains(response, f"#{search_run.pk}")
        self.assertContains(response, "hospital")

    def test_search_run_list_filters_by_status_source_and_campaign(self):
        self.login("run-filter")
        campaign = self.campaign()
        included = create_search_run(campaign=campaign, query="hospital", location="Campinas SP", source=SearchRun.Source.GOOGLE_MAPS, start=True)
        other_campaign = ProspectingCampaign.objects.create(name="Outra", product=self.product(name="Outro", slug="outro-filter", sku="OUT-F"), market_segment=self.segment(name="Indústria", slug="industria-filter"), location_description="RJ", objective="Teste")
        create_search_run(campaign=other_campaign, query="industria", source=SearchRun.Source.MANUAL, start=True)
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_list"), {"campaign": campaign.pk, "status": SearchRun.Status.RUNNING, "source": SearchRun.Source.GOOGLE_MAPS})
        self.assertContains(response, f"#{included.pk}")
        self.assertNotContains(response, "industria")

    def test_search_run_detail_lists_results_and_review_link(self):
        self.login("run-results")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", location="Campinas SP", start=True)
        result = SearchResult.objects.create(search_run=search_run, name="Hospital Santa Clara", phone="1933334444", city="Campinas", state="SP")
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertContains(response, result.name)
        self.assertContains(response, reverse("backoffice:sales_intelligence_result_detail", args=[result.pk]))
        self.assertContains(response, "Revisar")

    def test_search_run_complete_action_finishes_running_run(self):
        self.login("run-complete")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", start=True)
        response = self.client.post(reverse("backoffice:sales_intelligence_search_run_complete_form", args=[search_run.pk]))
        search_run.refresh_from_db()
        self.assertRedirects(response, reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertEqual(search_run.status, SearchRun.Status.COMPLETED)
        self.assertTrue(AuditLog.objects.filter(module="sales_intelligence.search_runs", object_id=str(search_run.pk), metadata__final_status=SearchRun.Status.COMPLETED).exists())

    def test_search_run_cancel_action_cancels_running_run(self):
        self.login("run-cancel")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", start=True)
        response = self.client.post(reverse("backoffice:sales_intelligence_search_run_cancel_form", args=[search_run.pk]))
        search_run.refresh_from_db()
        self.assertRedirects(response, reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertEqual(search_run.status, SearchRun.Status.CANCELLED)

    def test_invalid_state_transition_is_blocked(self):
        self.login("run-invalid")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", start=True)
        finish_search_run(search_run=search_run, status=SearchRun.Status.COMPLETED)
        response = self.client.post(reverse("backoffice:sales_intelligence_search_run_cancel_form", args=[search_run.pk]))
        search_run.refresh_from_db()
        self.assertRedirects(response, reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertEqual(search_run.status, SearchRun.Status.COMPLETED)

    def test_completed_run_hides_incompatible_actions(self):
        self.login("run-no-actions")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", start=True)
        finish_search_run(search_run=search_run, status=SearchRun.Status.COMPLETED)
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertNotContains(response, "Finalizar</button>", html=False)
        self.assertNotContains(response, "Cancelar</button>", html=False)

    def test_salesperson_can_use_operational_pages(self):
        self.login("run-salesperson", BackofficeRole.SALESPERSON)
        campaign = self.campaign()
        list_response = self.client.get(reverse("backoffice:sales_intelligence_campaign_list"))
        create_response = self.client.post(reverse("backoffice:sales_intelligence_search_run_create_form", args=[campaign.pk]), self.search_run_payload(query="clinica"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(create_response.status_code, 302)
        self.assertTrue(SearchRun.objects.filter(query="clinica", created_by__username="run-salesperson").exists())

    def test_commercial_manager_can_use_operational_pages(self):
        self.login("run-manager", BackofficeRole.COMMERCIAL_MANAGER)
        campaign = self.campaign()
        response = self.client.get(reverse("backoffice:sales_intelligence_campaign_detail", args=[campaign.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova pesquisa")

    def test_view_permission_can_read_but_not_manage(self):
        self.login("run-viewer", BackofficeRole.VIEWER)
        campaign = self.campaign()
        detail = self.client.get(reverse("backoffice:sales_intelligence_campaign_detail", args=[campaign.pk]))
        create = self.client.get(reverse("backoffice:sales_intelligence_search_run_create_form", args=[campaign.pk]))
        self.assertEqual(detail.status_code, 403)
        self.assertEqual(create.status_code, 403)

    def test_campaign_filters_by_status_product_and_segment(self):
        self.login("campaign-filter")
        product = self.product(name="Dune", slug="dune-campaign-filter", sku="DUNE-CF")
        segment = self.segment(name="Hospital", slug="hospital-campaign-filter")
        campaign = ProspectingCampaign.objects.create(name="Dune Hospitais", product=product, market_segment=segment, location_description="SP", objective="Demo", status=ProspectingCampaign.Status.ACTIVE)
        ProspectingCampaign.objects.create(name="Outra campanha", product=self.product(name="Outro", slug="outro-campaign-filter", sku="OUT-CF"), market_segment=self.segment(name="Escolas", slug="escolas-campaign-filter"), location_description="RJ", objective="Demo", status=ProspectingCampaign.Status.PAUSED)
        response = self.client.get(reverse("backoffice:sales_intelligence_campaign_list"), {"status": ProspectingCampaign.Status.ACTIVE, "product": product.pk, "segment": segment.pk})
        self.assertContains(response, campaign.name)
        self.assertNotContains(response, "Outra campanha")

    def test_search_run_detail_shows_failure_reason_when_failed(self):
        self.login("run-failed")
        search_run = create_search_run(campaign=self.campaign(), query="hospital", start=True)
        finish_search_run(search_run=search_run, status=SearchRun.Status.FAILED, failure_reason="DOM incompatível")
        response = self.client.get(reverse("backoffice:sales_intelligence_search_run_page", args=[search_run.pk]))
        self.assertContains(response, "DOM incompatível")
