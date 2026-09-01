from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase

from src.customers.models import Customer
from src.customers.normalization import apply_customer_match_normalization
from src.customers.normalization import normalize_domain_for_match
from src.customers.normalization import normalize_phone_for_match


class PhoneNormalizationTests(TestCase):
    def test_strips_plus_55_and_mask(self):
        self.assertEqual(normalize_phone_for_match("+55 11 99999-9999"), "11999999999")

    def test_strips_55_without_plus(self):
        self.assertEqual(normalize_phone_for_match("55 11 99999 9999"), "11999999999")

    def test_formatted_local_phone(self):
        self.assertEqual(normalize_phone_for_match("(11) 99999-9999"), "11999999999")

    def test_digits_only_local_phone(self):
        self.assertEqual(normalize_phone_for_match("11999999999"), "11999999999")

    def test_landline_with_country_code(self):
        self.assertEqual(normalize_phone_for_match("+55 (19) 3333-4444"), "1933334444")

    def test_empty_phone(self):
        self.assertEqual(normalize_phone_for_match(""), "")
        self.assertEqual(normalize_phone_for_match(None), "")

    def test_does_not_invent_ddd_or_complete_digits(self):
        self.assertEqual(normalize_phone_for_match("99999-9999"), "999999999")
        self.assertEqual(normalize_phone_for_match("55"), "55")


class DomainNormalizationTests(TestCase):
    def test_https_www_path_and_query(self):
        self.assertEqual(
            normalize_domain_for_match("https://www.empresa.com.br/contato?x=1#topo"),
            "empresa.com.br",
        )

    def test_http_without_www(self):
        self.assertEqual(normalize_domain_for_match("http://empresa.com.br"), "empresa.com.br")

    def test_bare_host_with_trailing_slash(self):
        self.assertEqual(normalize_domain_for_match("empresa.com.br/"), "empresa.com.br")

    def test_www_without_scheme(self):
        self.assertEqual(normalize_domain_for_match("www.empresa.com.br"), "empresa.com.br")

    def test_preserves_real_subdomain(self):
        self.assertEqual(normalize_domain_for_match("https://loja.empresa.com.br/home"), "loja.empresa.com.br")

    def test_strips_port(self):
        self.assertEqual(normalize_domain_for_match("https://empresa.com.br:443/path"), "empresa.com.br")

    def test_empty_and_malformed_domain(self):
        self.assertEqual(normalize_domain_for_match(""), "")
        self.assertEqual(normalize_domain_for_match(None), "")
        self.assertEqual(normalize_domain_for_match("   "), "")


class CustomerNormalizedFieldPersistenceTests(TestCase):
    def test_save_fills_normalized_fields(self):
        customer = Customer.objects.create(
            legal_name="Empresa Alfa",
            phone="+55 (11) 98888-7777",
            whatsapp="(11) 97777-6666",
            website="https://www.empresa.com.br/contato",
        )

        self.assertEqual(customer.normalized_phone, "11988887777")
        self.assertEqual(customer.normalized_whatsapp, "11977776666")
        self.assertEqual(customer.normalized_domain, "empresa.com.br")

    def test_update_fields_keeps_normalized_phone_in_sync(self):
        customer = Customer.objects.create(legal_name="Empresa Beta", phone="11999999999")
        customer.phone = "+55 21 98888-0000"
        customer.save(update_fields=["phone"])
        customer.refresh_from_db()

        self.assertEqual(customer.normalized_phone, "21988880000")

    def test_empty_identifiers_store_blank_normalized_values(self):
        customer = Customer.objects.create(legal_name="Sem contato")

        self.assertEqual(customer.normalized_phone, "")
        self.assertEqual(customer.normalized_whatsapp, "")
        self.assertEqual(customer.normalized_domain, "")

    def test_apply_helper_does_not_change_original_fields(self):
        customer = Customer(legal_name="Gamma", phone="(19) 3333-4444", website="https://www.hospitalabc.com.br/x")
        apply_customer_match_normalization(customer)

        self.assertEqual(customer.phone, "(19) 3333-4444")
        self.assertEqual(customer.website, "https://www.hospitalabc.com.br/x")
        self.assertEqual(customer.normalized_phone, "1933334444")
        self.assertEqual(customer.normalized_domain, "hospitalabc.com.br")

    def test_document_uniqueness_still_works_with_normalized_fields(self):
        Customer.objects.create(legal_name="A", document="12345678901")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Customer.objects.create(legal_name="B", document="123.456.789-01")
