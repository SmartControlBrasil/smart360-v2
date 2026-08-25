import json
from pathlib import Path
import re
import subprocess
import unittest
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import urljoin
from urllib.parse import urlsplit
from xml.etree import ElementTree

from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse

from src.commerce.models import Category
from src.commerce.models import Product
from src.institutional.presentation.authors import AUTHORS
from src.institutional.presentation.authors import MARCELO_CUSTODIO
from src.institutional.presentation.blog_editorial import BLOG_POST_EDITORIAL
from src.institutional.presentation.blog_posts import BLOG_POSTS
from src.institutional.presentation.blog_posts import BLOG_POSTS_LIST
from src.institutional.presentation.xyron_robot_pages import XYRON_ROBOT_PAGE_BY_KEY
from src.institutional.presentation.xyron_robot_pages import XYRON_ROBOT_PAGES
from src.institutional.presentation.xyron_pillar_pages import XYRON_PILLAR_PAGES
from src.institutional.infrastructure.django.templatetags.seo_tags import NOINDEX_ROUTE_NAMES

INSTITUTIONAL_MAIN_JS_CACHE_BUST = "20260825-preloader1"


class InstitutionalRoutesTests(TestCase):
    routes = (
        "home",
        "sistemas_websites_python",
        "manutencao_industrial_campo",
        "xyron",
        "mitsubishi_automacao_industrial",
        "about",
        "services",
        "blog",
        "login",
        "signup",
        "contact",
    )

    def test_all_institutional_routes_return_200(self):
        for route in self.routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(f"institutional:{route}"))

                self.assertEqual(response.status_code, 200)

    def test_home_uses_first_full_demo_template_and_static_assets(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertTemplateUsed(response, "institutional/demos/smart-control-brasil.html")
        self.assertContains(response, "institutional/css/main.css")
        self.assertContains(response, "institutional/js/main.js")
        self.assertContains(response, "banner-before")

    def test_smart_control_brasil_redirects_permanently_to_home(self):
        response = self.client.get(reverse("institutional:smart_control_brasil"))

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], reverse("institutional:home"))

    def test_legacy_urls_redirect_permanently_with_expected_location_and_query(self):
        redirects = (
            ("/sobre/", reverse("institutional:about")),
            (
                "/parceiros/mitsubishi-automacao/",
                reverse("institutional:mitsubishi_automacao_industrial"),
            ),
            (
                "/parceiros/automacao-industrial-clps/",
                reverse("institutional:mitsubishi_automacao_industrial"),
            ),
            ("/parceiros/xyron-robotics/", reverse("institutional:xyron")),
            ("/parceiros/agraz/", reverse("institutional:services")),
            ("/projetos/", reverse("institutional:services")),
            ("/projetos/detalhes/", reverse("institutional:services")),
            ("/blog/lista/", reverse("institutional:blog")),
            (
                "/blog/detalhes/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "selecao-controladores-ativos-alta-severidade"},
                ),
            ),
            (
                "/blog/automacao-industrial-conectada-gestao/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/dashboards-decisoes-melhores/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/iot-mudando-negocios/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/manutencao-tpm-confiabilidade-sistemas-automatizados/",
                reverse("institutional:manutencao_industrial_campo"),
            ),
            (
                "/blog/paineis-eletricos-automacao/",
                reverse("institutional:mitsubishi_automacao_industrial"),
            ),
            (
                "/blog/aplicacoes-reais-robos-brasil/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "inovacao-que-aparece-e-gera-valor"},
                ),
            ),
            (
                "/blog/robotica-escolas-empresas-cidades/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "inovacao-que-aparece-e-gera-valor"},
                ),
            ),
            (
                "/blog/integrar-sensores-maquinas-sistemas/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/automacao-conectada-maquinas-sensores-sistemas/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/dados-operacionais-empresa-inteligente/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "historico-indicadores-decisoes-consistentes"},
                ),
            ),
            ("/blog/pagina/2/", reverse("institutional:blog")),
            ("/faq/", reverse("institutional:home")),
        )

        for source, target in redirects:
            with self.subTest(source=source):
                response = self.client.get(f"{source}?utm_source=legacy&ref=old")

                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], f"{target}?utm_source=legacy&ref=old")

    def test_legacy_redirect_destinations_return_200_and_do_not_loop(self):
        redirects = (
            ("/sobre/", reverse("institutional:about")),
            (
                "/parceiros/mitsubishi-automacao/",
                reverse("institutional:mitsubishi_automacao_industrial"),
            ),
            (
                "/parceiros/automacao-industrial-clps/",
                reverse("institutional:mitsubishi_automacao_industrial"),
            ),
            ("/parceiros/xyron-robotics/", reverse("institutional:xyron")),
            ("/parceiros/agraz/", reverse("institutional:services")),
            ("/projetos/", reverse("institutional:services")),
            ("/projetos/detalhes/", reverse("institutional:services")),
            ("/blog/lista/", reverse("institutional:blog")),
            (
                "/blog/detalhes/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "selecao-controladores-ativos-alta-severidade"},
                ),
            ),
            (
                "/blog/automacao-industrial-conectada-gestao/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/dashboards-decisoes-melhores/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/iot-mudando-negocios/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/manutencao-tpm-confiabilidade-sistemas-automatizados/",
                reverse("institutional:manutencao_industrial_campo"),
            ),
            (
                "/blog/paineis-eletricos-automacao/",
                reverse("institutional:mitsubishi_automacao_industrial"),
            ),
            (
                "/blog/aplicacoes-reais-robos-brasil/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "inovacao-que-aparece-e-gera-valor"},
                ),
            ),
            (
                "/blog/robotica-escolas-empresas-cidades/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "inovacao-que-aparece-e-gera-valor"},
                ),
            ),
            (
                "/blog/integrar-sensores-maquinas-sistemas/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/automacao-conectada-maquinas-sensores-sistemas/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "informacao-precisa-para-agir-melhor"},
                ),
            ),
            (
                "/blog/dados-operacionais-empresa-inteligente/",
                reverse(
                    "institutional:blog_detail",
                    kwargs={"slug": "historico-indicadores-decisoes-consistentes"},
                ),
            ),
            ("/blog/pagina/2/", reverse("institutional:blog")),
            ("/faq/", reverse("institutional:home")),
        )

        for source, target in redirects:
            with self.subTest(source=source):
                self.assertNotEqual(source, target)
                response = self.client.get(source)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], target)

                destination_response = self.client.get(target)
                self.assertEqual(destination_response.status_code, 200)

    def test_removed_institutional_demo_routes_return_404(self):
        removed_paths = (
            "/servicos/detalhes/",
            "/equipe/",
            "/equipe/detalhes/",
            "/depoimentos/",
            "/planos/",
            "/carrinho/",
            "/lista-de-desejos/",
            "/checkout/",
            "/modelos/404/",
            "/ai-video-interaction-platform/",
            "/ai-web-solutions-startups/",
            "/robo-seguranca-condominios/",
            "/camara-climatica/",
            "/engenharia-serralheria-industrial/",
            "/livia/",
            "/camaras-climaticas/",
        )

        for removed_path in removed_paths:
            with self.subTest(removed_path=removed_path):
                response = self.client.get(removed_path)

                self.assertEqual(response.status_code, 404)

    def test_commerce_shop_routes_are_preserved_after_institutional_demo_cleanup(self):
        shop = self.client.get("/loja/")
        legacy_details = self.client.get("/loja/detalhes/")

        self.assertEqual(shop.status_code, 200)
        self.assertEqual(legacy_details.status_code, 200)

    def test_legacy_shop_details_does_not_render_known_demo_product_names(self):
        response = self.client.get("/loja/detalhes/")

        self.assertNotContains(response, "Opulent Citadel")
        self.assertNotContains(response, "Trickster Toadstool")

    def test_livia_widget_is_deferred(self):
        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode("utf-8")

        self.assertIn("https://livia.smartcontrolbrasil.com.br/widget.js", html)
        self.assertRegex(
            html,
            r"<script[^>]+defer[^>]+src=\"https://livia\.smartcontrolbrasil\.com\.br/widget\.js\"",
        )

    def test_lazy_images_use_async_decoding(self):
        response = self.client.get(reverse("institutional:home"))
        lazy_images = re.findall(r"<img[^>]+loading=\"lazy\"[^>]*>", response.content.decode("utf-8"))

        self.assertGreater(len(lazy_images), 0)
        for image in lazy_images:
            with self.subTest(image=image):
                self.assertIn("decoding=\"async\"", image)

    def test_menu_contains_named_solution_routes(self):
        response = self.client.get(reverse("institutional:home"))
        expected_labels = (
            "Início",
            "Sobre",
            "Soluções",
            "Manutenção Industrial",
            "Mitsubishi Automação",
            "Sistemas e Websites",
            "Xyron Robótica",
            "Blog",
            "Contato",
        )

        for label in expected_labels:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_internal_pages_use_canonical_base(self):
        response = self.client.get(reverse("institutional:about"))

        self.assertTemplateUsed(response, "institutional/base.html")
        self.assertContains(response, "breadcrumb__area")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Smart Control Brasil <no-reply@smartcontrolbrasil.com.br>",
    CONTACT_RECIPIENT_EMAIL="comercial@smartcontrolbrasil.com.br",
)
class ContactFormTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.url = reverse("institutional:contact")
        self.valid_data = {
            "nome": "  Maria Silva  ",
            "email": "maria@example.com",
            "telefone": "  (11) 99999-0000  ",
            "empresa": "  ACME Industrial  ",
            "assunto": "Projeto de automacao",
            "mensagem": "Preciso automatizar uma linha de montagem.",
            "aceite_privacidade": "1",
            "website": "",
        }

    def test_contact_get_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutional/pages/contact.html")

    def test_contact_form_contains_csrf_and_expected_action(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, f'action="{self.url}"')

    def test_valid_post_sends_exactly_one_email(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_uses_configured_recipient_sender_and_reply_to(self):
        self.client.post(self.url, self.valid_data)

        message = mail.outbox[0]
        self.assertEqual(message.to, ["comercial@smartcontrolbrasil.com.br"])
        self.assertEqual(message.from_email, "Smart Control Brasil <no-reply@smartcontrolbrasil.com.br>")
        self.assertEqual(message.reply_to, ["maria@example.com"])

    def test_email_body_contains_contact_details(self):
        self.client.post(self.url, self.valid_data)

        message = mail.outbox[0]
        self.assertEqual(message.subject, "[Site Smart Control Brasil] Projeto de automacao")
        for expected in (
            "Maria Silva",
            "maria@example.com",
            "(11) 99999-0000",
            "ACME Industrial",
            "Projeto de automacao",
            "Preciso automatizar uma linha de montagem.",
            "Autorizado",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, message.body)

    def test_empty_company_is_accepted(self):
        data = {**self.valid_data, "empresa": ""}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Nao informado", mail.outbox[0].body)

    def test_missing_required_fields_prevent_email(self):
        required_fields = (
            "nome",
            "email",
            "telefone",
            "assunto",
            "mensagem",
            "aceite_privacidade",
        )

        for field in required_fields:
            with self.subTest(field=field):
                mail.outbox = []
                data = {**self.valid_data}
                data.pop(field)

                response = self.client.post(self.url, data)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_prevents_email(self):
        data = {**self.valid_data, "email": "email-invalido"}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_privacy_acceptance_prevents_email(self):
        data = {**self.valid_data}
        data.pop("aceite_privacidade")

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_filled_honeypot_prevents_email(self):
        data = {**self.valid_data, "website": "https://spam.example"}

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_valid_post_redirects_to_contact_page(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, self.url)

    def test_email_backend_failure_does_not_expose_traceback(self):
        with patch(
            "src.institutional.presentation.views.EmailMessage.send",
            side_effect=SMTPException("smtp unavailable"),
        ):
            response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(
            response,
            "Não foi possível enviar sua solicitação agora. Tente novamente em alguns instantes.",
        )
        self.assertNotContains(response, "Traceback")
        self.assertNotContains(response, "smtp unavailable")

    def test_contact_form_uses_traditional_post_without_ajax_success_mask(self):
        main_js = Path("static/institutional/js/main.js").read_text()

        self.assertNotIn("$('#contact__form').submit", main_js)
        self.assertNotIn("Your message has been sent successfully.", main_js)
        self.assertNotIn("Something went wrong. Please try again later.", main_js)

    def test_contact_invalid_post_shows_portuguese_error_without_generate_lead(self):
        data = {**self.valid_data, "email": "email-invalido"}

        response = self.client.post(self.url, data)
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("Revise os dados informados e tente novamente.", html)
        self.assertNotIn('data-track-event="generate_lead"', html)

    def test_contact_success_tracks_generate_lead_only_after_real_success(self):
        response = self.client.post(self.url, self.valid_data, follow=True)
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Solicitação enviada com sucesso. Nossa equipe entrará em contato.", html)
        self.assertIn('data-track-event="generate_lead"', html)
        self.assertIn('data-track-on-load="true"', html)
        self.assertIn('data-track-location="contact_form"', html)

    def test_contact_smtp_failure_does_not_track_generate_lead(self):
        with patch(
            "src.institutional.presentation.views.EmailMessage.send",
            side_effect=SMTPException("smtp unavailable"),
        ):
            response = self.client.post(self.url, self.valid_data)

        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("Não foi possível enviar sua solicitação agora.", html)
        self.assertNotIn('data-track-event="generate_lead"', html)


class ConversionTrackingTests(TestCase):
    def test_header_primary_cta_points_to_contact(self):
        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode()

        self.assertIn('data-track-location="header"', html)
        self.assertIn('data-track-label="Solicitar orçamento"', html)
        self.assertIn(f'href="{reverse("institutional:contact")}"', html)
        self.assertIn("Solicitar orçamento", html)
        self.assertNotIn("Ver Produtos", html)

    def test_home_primary_cta_has_clear_copy_and_tracking(self):
        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode()

        self.assertIn("Solicitar contato", html)
        self.assertIn('data-track-location="home_hero"', html)
        self.assertIn('data-track-event="click_primary_cta"', html)

    def test_services_ctas_are_specific(self):
        response = self.client.get(reverse("institutional:services"))
        html = response.content.decode()

        for expected in (
            "Ver automação Mitsubishi",
            "Conhecer robôs Xyron",
            "Solicitar manutenção",
            "Planejar solução",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

    def test_littlebot_audio_section_has_followup_cta(self):
        response = self.client.get(reverse("institutional:xyron_littlebot"))
        html = response.content.decode()

        self.assertIn('data-track-location="littlebot_audio"', html)
        self.assertIn("Agendar demonstração", html)
        self.assertIn("robo-liro-inclusao-neurodivergentes.m4a", html)

    def test_tracking_script_pushes_expected_events_without_pii(self):
        main_js = Path("static/institutional/js/main.js").read_text()

        for event_name in (
            "click_whatsapp",
            "click_phone",
            "click_email",
        ):
            with self.subTest(event_name=event_name):
                self.assertIn(event_name, main_js)

        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode()

        self.assertIn("[data-track-event]", main_js)
        self.assertIn("window.dataLayer = window.dataLayer || []", main_js)
        self.assertIn("page_path: window.location.pathname", main_js)
        self.assertIn('data-track-event="click_primary_cta"', html)
        self.assertNotIn("telefone:", main_js)
        self.assertNotIn("email:", main_js)
        self.assertNotIn("mensagem:", main_js)


@override_settings(ALLOWED_HOSTS=["testserver", "smartcontrolbrasil.com.br"])
class TechnicalSeoTests(TestCase):
    AUTHOR_PERSON_ID = MARCELO_CUSTODIO.json_ld_id

    def assertBlogPostingAuthorAndDates(self, blog_posting, slug):
        editorial = BLOG_POST_EDITORIAL[slug]
        self.assertEqual(blog_posting["author"], {"@id": self.AUTHOR_PERSON_ID})
        self.assertEqual(blog_posting["datePublished"], editorial["date_published"])
        self.assertEqual(blog_posting["dateModified"], editorial["date_modified"])
        self.assertEqual(blog_posting["publisher"]["name"], "Smart Control Brasil")

    def assertCanonical(self, response, expected_url):
        html = response.content.decode()
        self.assertEqual(html.count('rel="canonical"'), 1)
        self.assertIn(f'<link rel="canonical" href="{expected_url}">', html)

    def assertTitle(self, response, expected_title):
        html = response.content.decode()
        self.assertIn(f"<title>{expected_title}</title>", html)

    def assertMetaDescription(self, response, expected_description):
        html = response.content.decode()
        self.assertIn(f'<meta name="description" content="{expected_description}">', html)

    def assertMetaProperty(self, response, property_name, expected_content):
        html = response.content.decode()
        self.assertIn(f'<meta property="{property_name}" content="{expected_content}">', html)

    def assertMetaName(self, response, name, expected_content):
        html = response.content.decode()
        self.assertIn(f'<meta name="{name}" content="{expected_content}">', html)

    def h1_texts(self, response):
        html = response.content.decode()
        matches = re.findall(r'<h1\b[^>]*>(.*?)</h1>', html, flags=re.I | re.S)
        return [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', match)).strip() for match in matches]

    def structured_data(self, response):
        html = response.content.decode()
        start_marker = '<script type="application/ld+json">'
        end_marker = '</script>'
        blocks = []
        start = html.find(start_marker)
        while start != -1:
            start += len(start_marker)
            end = html.find(end_marker, start)
            self.assertNotEqual(end, -1)
            blocks.append(json.loads(html[start:end]))
            start = html.find(start_marker, end + len(end_marker))
        return blocks

    def graph_items(self, response, item_type=None):
        items = []
        for payload in self.structured_data(response):
            graph = payload.get("@graph", [])
            items.extend(graph if isinstance(graph, list) else [graph])
        if item_type:
            return [item for item in items if item.get("@type") == item_type]
        return items

    def sitemap_urls(self):
        response = self.client.get(
            "/sitemap.xml",
            HTTP_HOST="smartcontrolbrasil.com.br",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        root = ElementTree.fromstring(response.content.decode())
        return [
            element.text
            for element in root.findall(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}url/"
                "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
            )
        ]

    def test_home_includes_approved_google_tag_once(self):
        response = self.client.get("/")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(html.count("https://www.googletagmanager.com/gtag/js?id=G-9XGJDZ0N87"), 1)
        self.assertEqual(html.count("gtag('config', 'G-9XGJDZ0N87')"), 1)
        self.assertNotIn("G-X9BGRJ75B7", html)

    def test_global_theme_scripts_are_deferred_in_dependency_order(self):
        response = self.client.get("/")
        html = response.content.decode()
        scripts = (
            "institutional/js/vendor/jquery-3.7.1.min.js",
            "institutional/js/vendor/chroma.min.js",
            "institutional/js/vendor/bootstrap.bundle.min.js",
            "institutional/js/plugins/meanmenu.min.js",
            "institutional/js/plugins/gsap.js",
            "institutional/js/plugins/ScrollSmoother.js",
            "institutional/js/plugins/ScrollToPlugin.js",
            "institutional/js/plugins/ScrollTrigger.js",
            "institutional/js/plugins/SplitText.js",
            "institutional/js/plugins/swiper.min.js",
            "institutional/js/plugins/wow.js",
            f"institutional/js/main.js?v={INSTITUTIONAL_MAIN_JS_CACHE_BUST}",
        )

        previous_position = -1
        for script in scripts:
            with self.subTest(script=script):
                tag = f'<script defer src="/static/{script}"></script>'
                position = html.find(tag)
                self.assertGreater(position, previous_position)
                previous_position = position

        self.assertEqual(html.count("institutional/js/vendor/jquery-3.7.1.min.js"), 1)
        self.assertEqual(
            html.count(f"institutional/js/main.js?v={INSTITUTIONAL_MAIN_JS_CACHE_BUST}"),
            1,
        )

    def test_home_lcp_image_is_prioritized_without_lazy_loading(self):
        response = self.client.get("/")
        html = response.content.decode()
        image_start = html.find("institutional/imgs/home/recepicionista-atendento.webp")
        self.assertNotEqual(image_start, -1)
        image_tag = html[html.rfind("<img", 0, image_start):html.find(">", image_start) + 1]

        self.assertIn('width="381"', image_tag)
        self.assertIn('height="571"', image_tag)
        self.assertIn('loading="eager"', image_tag)
        self.assertIn('fetchpriority="high"', image_tag)
        self.assertNotIn('loading="lazy"', image_tag)

    def test_home_below_fold_images_use_lazy_loading(self):
        response = self.client.get("/")

        self.assertContains(
            response,
            'institutional/imgs/blog/controladores-ativos-para-ambientes-de-alta-severidade.webp',
        )
        self.assertContains(response, 'width="380" height="260" loading="lazy" decoding="async"')

    def test_home_uses_metadata_title_description_and_canonical(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Smart Control Brasil | Automação Industrial, Robótica e Sistemas")
        self.assertMetaDescription(
            response,
            "Soluções em automação industrial, robótica, manutenção técnica, "
            "integração de sistemas e desenvolvimento de software para empresas e indústrias.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/")
        self.assertEqual(
            self.h1_texts(response),
            ["Automação Industrial, Robótica e Sistemas para Transformar sua Operação"],
        )
        self.assertNotContains(response, 'name="robots"')

    def test_home_includes_open_graph_and_twitter_card_metadata(self):
        response = self.client.get("/")
        image_url = "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/banner-6-img-1.png"

        self.assertMetaProperty(response, "og:title", "Smart Control Brasil | Automação Industrial, Robótica e Sistemas")
        self.assertMetaProperty(
            response,
            "og:description",
            "Soluções em automação industrial, robótica, manutenção técnica, "
            "integração de sistemas e desenvolvimento de software para empresas e indústrias.",
        )
        self.assertMetaProperty(response, "og:url", "https://www.smartcontrolbrasil.com.br/")
        self.assertMetaProperty(response, "og:type", "website")
        self.assertMetaProperty(response, "og:image", image_url)
        self.assertMetaProperty(response, "og:image:width", "1290")
        self.assertMetaProperty(response, "og:image:height", "670")
        self.assertMetaProperty(
            response,
            "og:image:alt",
            "Robótica, automação e sistemas inteligentes da Smart Control Brasil",
        )
        self.assertMetaProperty(response, "og:site_name", "Smart Control Brasil")
        self.assertMetaProperty(response, "og:locale", "pt_BR")
        self.assertMetaName(response, "twitter:card", "summary_large_image")
        self.assertMetaName(response, "twitter:title", "Smart Control Brasil | Automação Industrial, Robótica e Sistemas")
        self.assertMetaName(
            response,
            "twitter:description",
            "Soluções em automação industrial, robótica, manutenção técnica, "
            "integração de sistemas e desenvolvimento de software para empresas e indústrias.",
        )
        self.assertMetaName(response, "twitter:image", image_url)
        self.assertMetaName(
            response,
            "twitter:image:alt",
            "Robótica, automação e sistemas inteligentes da Smart Control Brasil",
        )
        self.assertNotIn('content="/static/', response.content.decode())

    def test_home_includes_organization_and_website_json_ld(self):
        response = self.client.get("/")

        organizations = self.graph_items(response, "Organization")
        websites = self.graph_items(response, "WebSite")

        self.assertEqual(len(organizations), 1)
        self.assertEqual(organizations[0]["name"], "Smart Control Brasil")
        self.assertEqual(organizations[0]["url"], "https://www.smartcontrolbrasil.com.br")
        self.assertEqual(
            organizations[0]["logo"],
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/header/logo-cores-03.webp",
        )
        self.assertEqual(organizations[0]["email"], "comercial@smartcontrolbrasil.com.br")
        self.assertEqual(organizations[0]["telephone"], "+551151968525")
        self.assertEqual(organizations[0]["areaServed"], "Brasil")
        self.assertIn("Automação Industrial", organizations[0]["knowsAbout"])
        self.assertIn("Manutenção Industrial", organizations[0]["knowsAbout"])
        self.assertEqual(len(websites), 1)
        self.assertEqual(websites[0]["name"], "Smart Control Brasil")
        self.assertEqual(websites[0]["url"], "https://www.smartcontrolbrasil.com.br")
        self.assertNotIn("SearchAction", response.content.decode())

    def test_home_includes_faq_page_json_ld_only_on_home(self):
        response = self.client.get("/")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(faq_pages), 1)
        questions = faq_pages[0]["mainEntity"]
        self.assertEqual(len(questions), 4)
        self.assertEqual(questions[0]["name"], "Como começa um projeto com a Smart Control Brasil?")
        self.assertIn("análise detalhada do cenário atual", questions[0]["acceptedAnswer"]["text"])

        blog_response = self.client.get("/blog/")
        self.assertEqual(self.graph_items(blog_response, "FAQPage"), [])

    def test_home_links_are_indexable_and_not_empty_after_seo_cleanup(self):
        response = self.client.get("/")
        html = response.content.decode()

        self.assertNotIn("href=\"#\"", html)
        self.assertNotIn("/planos/", html)
        self.assertNotIn(reverse("institutional:blog_details"), html)
        self.assertIn(reverse("institutional:manutencao_industrial_campo"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "selecao-controladores-ativos-alta-severidade"}), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "convergencia-robotica-ia-firmwares-dedicados"}), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "eliminar-gargalos-autonomia-previsibilidade"}), html)
        self.assertNotIn("form action=\"#\"", html)


    def test_contact_page_has_commercial_h1_content_links_nap_and_schemas(self):
        response = self.client.get("/contato/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        canonical = "https://www.smartcontrolbrasil.com.br/contato/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Contato e Orçamento em Automação Industrial | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Fale com a Smart Control Brasil para solicitar orçamento, diagnóstico técnico "
            "ou atendimento comercial em automação, robótica e sistemas.",
        )
        self.assertCanonical(response, canonical)
        self.assertMetaProperty(response, "og:url", canonical)
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Contato e Orçamento em Automação Industrial e Robótica"],
        )

        for expected in (
            "Conte-nos sobre seu projeto",
            "automação industrial",
            "Mitsubishi Electric",
            "robótica Xyron",
            "manutenção industrial e retrofit",
            "integração de dados",
            "sistemas web em Python/Django",
            'href="tel:+551151968525"',
            "(11) 5196-8525",
            'href="mailto:comercial@smartcontrolbrasil.com.br"',
            "comercial@smartcontrolbrasil.com.br",
            "R. Agnaldo Alves Silva - Jardim Maristela",
            "Itapevi - SP, 06663-160",
            "Autorizo o uso dos dados informados",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_link in (
            reverse("institutional:services"),
            reverse("institutional:manutencao_industrial_campo"),
            reverse("institutional:mitsubishi_automacao_industrial"),
            reverse("institutional:xyron"),
            reverse("institutional:sistemas_websites_python"),
        ):
            with self.subTest(expected_link=expected_link):
                self.assertIn(f'href="{expected_link}"', html)

        faq_questions = [
            "Quais serviços posso solicitar pelo formulário?",
            "Posso solicitar atendimento para manutenção e retrofit?",
            "Posso falar sobre projetos de automação Mitsubishi Electric ou robótica Xyron?",
            "Quais informações ajudam na análise de uma solicitação técnica?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(f"<h3>{question}</h3>", html)

        organizations = self.graph_items(response, "Organization")
        contact_pages = self.graph_items(response, "ContactPage")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(organizations), 1)
        organization = organizations[0]
        self.assertEqual(organization["@id"], "https://www.smartcontrolbrasil.com.br/#organization")
        self.assertEqual(organization["name"], "Smart Control Brasil")
        self.assertEqual(organization["telephone"], "+551151968525")
        self.assertEqual(organization["email"], "comercial@smartcontrolbrasil.com.br")
        self.assertEqual(
            organization["address"],
            {
                "@type": "PostalAddress",
                "streetAddress": "R. Agnaldo Alves Silva - Jardim Maristela",
                "addressLocality": "Itapevi",
                "addressRegion": "SP",
                "postalCode": "06663-160",
                "addressCountry": "BR",
            },
        )

        self.assertEqual(len(contact_pages), 1)
        self.assertEqual(contact_pages[0]["url"], canonical)
        self.assertEqual(contact_pages[0]["provider"], {"@id": organization["@id"]})
        self.assertEqual(contact_pages[0]["about"], {"@id": organization["@id"]})

        self.assertEqual(len(breadcrumbs), 1)
        items = breadcrumbs[0]["itemListElement"]
        self.assertEqual([item["name"] for item in items], ["Início", "Contato"])
        self.assertEqual(items[0]["item"], "https://www.smartcontrolbrasil.com.br/")
        self.assertEqual(items[1]["item"], canonical)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        for item in faq_entities:
            answer = item["acceptedAnswer"]["text"]
            self.assertIn(answer, html)

        self.assertNotIn("GeoCoordinates", html)
        self.assertNotIn("openingHours", html)
        self.assertNotIn("AggregateRating", html)
        self.assertNotIn("priceRange", html)


    def test_about_page_uses_metadata_h1_canonical_and_indexing(self):
        response = self.client.get("/empresa/?utm_source=google")

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Empresa de Automação, Robótica e Sistemas | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Conheça a Smart Control Brasil, empresa especializada em automação industrial, "
            "robótica, engenharia, manutenção técnica e desenvolvimento de sistemas.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/empresa/")
        self.assertEqual(
            self.h1_texts(response),
            ["Smart Control Brasil — Automação, Robótica e Sistemas"],
        )
        self.assertNotContains(response, 'name="robots"')

    def test_about_page_template_residues_and_links_are_clean(self):
        response = self.client.get("/empresa/")
        html = response.content.decode()

        for forbidden in ("./assets/", 'alt="img not found"', 'alt="img not fount"', 'href="#"'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)
        self.assertNotIn(reverse("institutional:blog_details"), html)
        self.assertNotIn("/equipe/", html)
        self.assertIn(reverse("institutional:services"), html)
        self.assertIn(reverse("institutional:xyron"), html)
        self.assertIn(reverse("institutional:mitsubishi_automacao_industrial"), html)
        self.assertIn(reverse("institutional:manutencao_industrial_campo"), html)
        self.assertIn(reverse("institutional:sistemas_websites_python"), html)
        self.assertIn(reverse("institutional:blog"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "equipamentos-sistemas-para-evoluir"}), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "inovacao-que-aparece-e-gera-valor"}), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "informacao-precisa-para-agir-melhor"}), html)
        self.assertIn("Responsabilidade Técnica e Editorial", html)
        self.assertIn(reverse("institutional:author_detail", kwargs={"slug": MARCELO_CUSTODIO.slug}), html)

    def test_about_page_includes_breadcrumb_and_about_page_json_ld(self):
        response = self.client.get("/empresa/")

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        about_pages = self.graph_items(response, "AboutPage")

        self.assertEqual(len(breadcrumbs), 1)
        items = breadcrumbs[0]["itemListElement"]
        self.assertEqual([item["position"] for item in items], [1, 2])
        self.assertEqual(items[0]["name"], "Início")
        self.assertEqual(items[0]["item"], "https://www.smartcontrolbrasil.com.br/")
        self.assertEqual(items[1]["name"], "Sobre")
        self.assertEqual(items[1]["item"], "https://www.smartcontrolbrasil.com.br/empresa/")
        self.assertEqual(len(about_pages), 1)
        self.assertEqual(about_pages[0]["url"], "https://www.smartcontrolbrasil.com.br/empresa/")
        self.assertEqual(about_pages[0]["mainEntity"]["name"], "Smart Control Brasil")

    def test_solution_page_includes_breadcrumb_json_ld(self):
        response = self.client.get("/xyron/?utm_source=google")

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        self.assertEqual(len(breadcrumbs), 1)
        items = breadcrumbs[0]["itemListElement"]
        self.assertEqual([item["position"] for item in items], [1, 2])
        self.assertEqual(items[0]["name"], "Início")
        self.assertEqual(items[0]["item"], "https://www.smartcontrolbrasil.com.br/")
        self.assertEqual(items[1]["name"], "Xyron Robotics")
        self.assertEqual(items[1]["item"], "https://www.smartcontrolbrasil.com.br/xyron/")

    def test_services_has_seo_content_links_and_schemas(self):
        response = self.client.get("/servicos/?utm_source=google&utm_campaign=x&gclid=abc")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Serviços de Automação Industrial, Robótica e Software | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Conheça os serviços da Smart Control Brasil em automação industrial, robótica Xyron, "
            "manutenção industrial e desenvolvimento de sistemas sob medida.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/servicos/")
        self.assertEqual(
            self.h1_texts(response),
            ["Serviços de Automação, Robótica, Manutenção e Sistemas"],
        )
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, "gclid")
        self.assertNotContains(response, 'name="robots"')

        for expected in (
            "Automação Industrial",
            "Robótica Inteligente",
            "Manutenção Industrial",
            "Sistemas e Soluções Digitais",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for forbidden in (
            "Seken",
            "Incessantly",
            "Fast Content Creation",
            "AI Generated Outcomes",
            "Transaction Portals",
            "Bilingual and beyond",
            "Assistance Platform",
            "Common Questions",
            "Fusce interdum",
            "Sed interdum",
            "Mattis eros",
            'href="#"',
            'alt="fast-content-img',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        self.assertIn(reverse("institutional:about"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(reverse("institutional:mitsubishi_automacao_industrial"), html)
        self.assertIn(reverse("institutional:xyron"), html)
        self.assertIn(reverse("institutional:manutencao_industrial_campo"), html)
        self.assertIn(reverse("institutional:sistemas_websites_python"), html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")
        services = self.graph_items(response, "Service")

        self.assertEqual(len(breadcrumbs), 1)
        items = breadcrumbs[0]["itemListElement"]
        self.assertEqual([item["name"] for item in items], ["Início", "Serviços"])
        self.assertEqual(items[1]["item"], "https://www.smartcontrolbrasil.com.br/servicos/")
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(len(faq_pages[0]["mainEntity"]), 4)
        self.assertEqual(faq_pages[0]["mainEntity"][0]["name"], "Quais serviços a Smart Control Brasil oferece?")
        self.assertEqual(len(services), 1)
        self.assertIn("Manutenção Industrial", services[0]["serviceType"])

    def test_blog_article_uses_title_metadata_h1_and_canonical(self):
        response = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        post = BLOG_POSTS["selecao-controladores-ativos-alta-severidade"]
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, post.get("seo_title") or f"{post['title']} | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(
            response,
            "https://www.smartcontrolbrasil.com.br/blog/selecao-controladores-ativos-alta-severidade/",
        )
        self.assertEqual(html.count("<h1"), 1)
        self.assertIn(f'<h1 class="breadcrumb__title">{post["title"]}</h1>', html)
        self.assertNotContains(response, 'name="robots"')

    def test_severe_environment_article_has_expanded_editorial_depth_and_faq_schema(self):
        response = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        html = response.content.decode()
        post = BLOG_POSTS["selecao-controladores-ativos-alta-severidade"]

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Controladores para Ambientes Severos | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(
            response,
            "https://www.smartcontrolbrasil.com.br/blog/selecao-controladores-ativos-alta-severidade/",
        )
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "O ambiente deve fazer parte da especificação",
            "Grau de proteção não resolve tudo sozinho",
            "CLP: confiabilidade antes de capacidade excessiva",
            "IHM também precisa ser especificada para o ambiente",
            "Inversores e acionamentos",
            "Interferência eletromagnética e instalação",
            "Temperatura e dissipação térmica do painel",
            "Manutenibilidade também deve entrar na especificação",
            "Checklist para especificação",
            "Exemplo de aplicação",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "grau de proteção",
            "interferência eletromagnética",
            "temperatura",
            "CLP",
            "IHM",
            "Inversores",
            "MTTR",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        self.assertIn('href="/mitsubishi-automacao-industrial/"', html)
        self.assertIn('href="/manutencao-industrial-campo/"', html)
        self.assertIn('href="/servicos/"', html)
        self.assertIn("Considere, por exemplo", html)
        self.assertIn("O checklist abaixo não substitui análise técnica", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["articleSection"], "Engenharia de Aplicação")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "selecao-controladores-ativos-alta-severidade")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

    def test_strategic_pages_have_single_descriptive_h1_and_clean_on_page_markers(self):
        expectations = {
            "/xyron/": "Xyron Robotics",
            "/mitsubishi-automacao-industrial/": "Mitsubishi Automação Industrial",
            "/manutencao-industrial-campo/": "Manutenção Industrial",
            "/sistemas-websites-python/": "Sistemas Web, Websites e Soluções em Python",
        }
        forbidden = (
            'alt="image"',
            'alt="img not found"',
            'alt="img not fount"',
            'Read More',
            'Learn More',
            'Home</a>',
            './assets/',
        )

        for path, expected_h1_fragment in expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.content.decode()
                h1s = self.h1_texts(response)

                self.assertEqual(len(h1s), 1)
                self.assertIn(expected_h1_fragment, h1s[0])
                for marker in forbidden:
                    self.assertNotIn(marker, html)

    def test_indexable_breadcrumbs_use_inicio_text(self):
        expectations = (
            ("/xyron/", "Xyron Robotics"),
            ("/blog/selecao-controladores-ativos-alta-severidade/", "Blog"),
        )

        for path, final_label in expectations:
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.content.decode()

                self.assertIn('>Início</a>', html)
                self.assertIn(final_label, html)
                self.assertNotIn('>Home</a>', html)

    def test_header_search_does_not_submit_fake_home_search(self):
        response = self.client.get("/")
        html = response.content.decode()

        self.assertIn('role="search"', html)
        self.assertIn('onsubmit="return false"', html)
        self.assertNotIn('name="s"', html)

    def test_global_payload_does_not_load_unused_jquery_ui_datepicker(self):
        response = self.client.get("/")
        html = response.content.decode()
        main_js = Path("static/institutional/js/main.js").read_text()

        self.assertNotIn("jquery-ui.min.js", html)
        self.assertNotIn("#datepicker", main_js)
        self.assertNotIn(".datepicker(", main_js)

    def test_external_demo_audio_source_is_not_referenced_in_project_sources(self):
        searchable_roots = (
            Path("templates"),
            Path("src"),
            Path("static"),
            Path("config"),
        )

        vendor_name = "sound" + "helix"
        vendor_domain = "www." + vendor_name + ".com"

        for root in searchable_roots:
            for source in root.rglob("*"):
                if source.is_file() and source.suffix.lower() not in {".pyc", ".webp", ".png", ".jpg", ".jpeg", ".m4a", ".woff", ".woff2"}:
                    with self.subTest(source=source):
                        content = source.read_text(errors="ignore").lower()
                        self.assertNotIn(vendor_name, content)
                        self.assertNotIn(vendor_domain, content)

    def test_littlebot_uses_local_institutional_audio(self):
        response = self.client.get(reverse("institutional:xyron_littlebot"))
        html = response.content.decode()
        audio_path = "institutional/audio/robo-liro-inclusao-neurodivergentes.m4a"

        self.assertEqual(response.status_code, 200)
        self.assertIn(audio_path, html)
        self.assertIn('data-audio-src="/static/institutional/audio/robo-liro-inclusao-neurodivergentes.m4a"', html)
        self.assertIn('aria-label="Ouvir áudio institucional sobre LIRO e inclusão"', html)
        self.assertIn('class="audio fa-sharp fa-solid fa-play"', html)
        self.assertNotIn("sound" + "helix", html.lower())
        self.assertIsNotNone(finders.find(audio_path))

    def test_mitsubishi_audio_template_residue_was_removed(self):
        response = self.client.get(reverse("institutional:mitsubishi_automacao_industrial"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("hero-10-slider__area", html)
        self.assertNotIn('class="audio', html)
        self.assertNotIn("robo-liro-inclusao-neurodivergentes", html)
        self.assertNotIn("sound" + "helix", html.lower())

    def test_commercial_solution_routes_are_indexable(self):
        expected_canonicals = {
            "/xyron/": "https://www.smartcontrolbrasil.com.br/xyron/",
            "/mitsubishi-automacao-industrial/": "https://www.smartcontrolbrasil.com.br/mitsubishi-automacao-industrial/",
            "/manutencao-industrial-campo/": "https://www.smartcontrolbrasil.com.br/manutencao-industrial-campo/",
            "/sistemas-websites-python/": "https://www.smartcontrolbrasil.com.br/sistemas-websites-python/",
        }

        for path, canonical in expected_canonicals.items():
            with self.subTest(path=path):
                response = self.client.get(f"{path}?utm_source=google")

                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'name="robots"')
                self.assertCanonical(response, canonical)
                self.assertMetaProperty(response, "og:url", canonical)
                self.assertMetaProperty(response, "og:type", "website")
                expected_images = {
                    "/manutencao-industrial-campo/": "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/retrofite-painel-eletronico.webp",
                    "/mitsubishi-automacao-industrial/": "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/clp-e-acionanentos.webp",
                }
                expected_image = expected_images.get(
                    path,
                    "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/banner-6-img-1.png",
                )
                self.assertMetaProperty(response, "og:image", expected_image)
                self.assertMetaProperty(response, "og:site_name", "Smart Control Brasil")
                self.assertMetaProperty(response, "og:locale", "pt_BR")
                self.assertMetaName(response, "twitter:card", "summary_large_image")
                self.assertIn('<meta property="og:title" content="', response.content.decode())
                self.assertIn('<meta property="og:description" content="', response.content.decode())
                self.assertIn('<meta name="twitter:title" content="', response.content.decode())
                self.assertIn('<meta name="twitter:description" content="', response.content.decode())
                self.assertIn('<meta name="twitter:image" content="https://', response.content.decode())

    def test_temporarily_disabled_commercial_landings_return_404(self):
        disabled_paths = (
            "/engenharia-serralheria-industrial/",
            "/camara-climatica/",
            "/robo-seguranca-condominios/",
        )

        for path in disabled_paths:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 404)
                self.assertTemplateUsed(response, "institutional/404.html")
                self.assertTitle(response, "Página não encontrada | Smart Control Brasil")
                self.assertContains(response, '<meta name="robots" content="noindex,follow">', status_code=404)
                self.assertNotContains(response, 'BreadcrumbList', status_code=404)

    def test_commercial_solution_metadata_is_specific(self):
        metadata_expectations = (
            (
                "/xyron/",
                "Robôs Inteligentes Xyron Robotics | Smart Control Brasil",
                "Conheça as soluções de robótica inteligente da Xyron Robotics para educação, "
                "atendimento, interação e aplicações profissionais com a Smart Control Brasil.",
            ),
            (
                "/mitsubishi-automacao-industrial/",
                "Automação Industrial Mitsubishi Electric | Smart Control Brasil",
                "Automação industrial Mitsubishi Electric com CLPs, IHMs, inversores, "
                "servoacionamentos, integração, retrofit, comissionamento e suporte técnico.",
            ),
            (
                "/manutencao-industrial-campo/",
                "Manutenção Industrial e Assistência Técnica | Smart Control Brasil",
                "Manutenção industrial e assistência técnica em campo com diagnóstico, "
                "preventiva, corretiva, comissionamento, retrofit, automação e painéis elétricos.",
            ),
            (
                "/sistemas-websites-python/",
                "Sistemas Web, Websites e Desenvolvimento Python | Smart Control Brasil",
                "Desenvolvimento de sistemas web, websites empresariais, plataformas, integrações "
                "e soluções em Python e Django para digitalização de processos.",
            ),
        )

        for path, expected_title, expected_description in metadata_expectations:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertTitle(response, expected_title)
                self.assertMetaDescription(response, expected_description)

    def test_sistemas_websites_python_landing_has_content_links_schemas_and_no_fake_reviews(self):
        response = self.client.get("/sistemas-websites-python/?utm_source=google&utm_campaign=x")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Sistemas Web, Websites e Desenvolvimento Python | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Desenvolvimento de sistemas web, websites empresariais, plataformas, integrações "
            "e soluções em Python e Django para digitalização de processos.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/sistemas-websites-python/")
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Sistemas Web, Websites e Soluções em Python"],
        )

        for expected in (
            "Python",
            "Django",
            "Sistemas Web",
            "Websites",
            "Portais",
            "Dashboards",
            "APIs",
            "Inteligência Artificial",
            "PostgreSQL",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for anchor in (
            "#python-django",
            "#portais",
            "#dashboards",
            "#automacao-digital",
            "#ia-aplicada",
            "#integracoes",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(f'id="{anchor[1:]}"', html)

        self.assertNotIn('href="#"', html)
        repeated = (
            "Desenvolvemos soluções digitais com foco em processos reais, organização dos dados, "
            "facilidade de uso e evolução contínua do sistema."
        )
        self.assertNotIn(repeated, html)
        self.assertEqual(html.count('class="testimonial-2__item-dec"'), 9)
        self.assertIn("Arquitetura sob medida", html)
        self.assertIn("APIs e integrações", html)
        self.assertIn("IA aplicada", html)

        self.assertIn(reverse("institutional:services"), html)
        self.assertIn(reverse("institutional:about"), html)
        self.assertIn(reverse("institutional:mitsubishi_automacao_industrial"), html)
        self.assertIn(reverse("institutional:manutencao_industrial_campo"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(
            reverse(
                "institutional:blog_detail",
                kwargs={"slug": "equipamentos-sistemas-para-evoluir"},
            ),
            html,
        )

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")
        services = self.graph_items(response, "Service")
        reviews = self.graph_items(response, "Review")
        aggregate_ratings = self.graph_items(response, "AggregateRating")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Sistemas Web e Desenvolvimento Python"],
        )
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(len(faq_pages[0]["mainEntity"]), 4)
        self.assertEqual(
            faq_pages[0]["mainEntity"][0]["name"],
            "Vocês desenvolvem sistemas totalmente personalizados?",
        )
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["name"], "Desenvolvimento de Sistemas Web e Soluções em Python")
        self.assertIn("Aplicações Django", services[0]["serviceType"])
        self.assertNotIn("areaServed", services[0])
        self.assertEqual(reviews, [])
        self.assertEqual(aggregate_ratings, [])

    def test_mitsubishi_landing_has_technical_content_links_schemas_and_clean_links(self):
        response = self.client.get("/mitsubishi-automacao-industrial/?utm_source=google&utm_campaign=x")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Automação Industrial Mitsubishi Electric | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Automação industrial Mitsubishi Electric com CLPs, IHMs, inversores, "
            "servoacionamentos, integração, retrofit, comissionamento e suporte técnico.",
        )
        self.assertCanonical(
            response,
            "https://www.smartcontrolbrasil.com.br/mitsubishi-automacao-industrial/",
        )
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Mitsubishi Automação Industrial: Controle, Movimento e Dados"],
        )

        for expected in (
            "Mitsubishi Electric",
            "CLP",
            "IHM",
            "Inversores",
            "Servo",
            "MELFA",
            "Automação Industrial",
            "MELSEC",
            "GX Works",
            "CC-Link",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for anchor in ("#clps", "#ihms", "#inversores", "#motion", "#melfa", "#supervisao"):
            with self.subTest(anchor=anchor):
                self.assertIn(f'id="{anchor[1:]}"', html)
                self.assertIn(f'href="{anchor}"', html)

        for forbidden in (
            'href="#"',
            "project_details",
            'href="/servicos/detalhes/"',
            "distribuidor oficial",
            "revendedor autorizado",
            "integrador certificado",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        self.assertIn(reverse("institutional:services"), html)
        self.assertIn(reverse("institutional:manutencao_industrial_campo"), html)
        self.assertIn(reverse("institutional:sistemas_websites_python"), html)
        self.assertIn(reverse("institutional:about"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(
            reverse(
                "institutional:blog_detail",
                kwargs={"slug": "selecao-controladores-ativos-alta-severidade"},
            ),
            html,
        )

        self.assertMetaProperty(
            response,
            "og:image",
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/clp-e-acionanentos.webp",
        )
        self.assertMetaProperty(response, "og:image:width", "220")
        self.assertMetaProperty(response, "og:image:height", "260")
        self.assertMetaProperty(response, "og:image:alt", "CLP Mitsubishi Electric em aplicação de automação")

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")
        services = self.graph_items(response, "Service")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Mitsubishi Automação Industrial"],
        )
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(len(faq_pages[0]["mainEntity"]), 5)
        self.assertEqual(
            faq_pages[0]["mainEntity"][0]["name"],
            "A Smart Control Brasil vende componentes Mitsubishi Electric?",
        )
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["name"], "Automação Industrial Mitsubishi Electric")
        self.assertIn("Programação de CLP", services[0]["serviceType"])
        self.assertNotIn("areaServed", services[0])

    def test_manutencao_industrial_landing_has_content_links_schemas_and_social_image(self):
        response = self.client.get("/manutencao-industrial-campo/?utm_source=google&utm_campaign=x")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Manutenção Industrial e Assistência Técnica | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Manutenção industrial e assistência técnica em campo com diagnóstico, "
            "preventiva, corretiva, comissionamento, retrofit, automação e painéis elétricos.",
        )
        self.assertCanonical(
            response,
            "https://www.smartcontrolbrasil.com.br/manutencao-industrial-campo/",
        )
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Manutenção Industrial e Assistência Técnica em Campo"],
        )

        for expected in (
            "Manutenção Industrial",
            "Assistência Técnica",
            "manutenção preventiva",
            "corretiva",
            "Painéis Elétricos",
            "automação industrial",
            "Confiabilidade",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        tab_titles = (
            "Manutenção de sistemas",
            "Manutenção de máquinas",
            "Manutenção e retrofit",
            "Diagnóstico de",
            "Manutenção orientada",
        )
        for title in tab_titles:
            with self.subTest(tab_title=title):
                self.assertIn(title, html)
        self.assertEqual(len(set(tab_titles)), 5)

        repeated_title = "Manutenção industrial <br> com diagnóstico e confiabilidade"
        self.assertNotIn(repeated_title, html)
        for forbidden in (
            'alt="not found"',
            'alt="fast-content-img"',
            'alt="latest-blog-img"',
            'href="/camara-climatica/"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        self.assertIn(reverse("institutional:services"), html)
        self.assertIn(reverse("institutional:mitsubishi_automacao_industrial"), html)
        self.assertIn(reverse("institutional:about"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(
            reverse(
                "institutional:blog_detail",
                kwargs={"slug": "reducao-paradas-inesperadas-planejamento-tecnico"},
            ),
            html,
        )

        self.assertMetaProperty(
            response,
            "og:image",
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/retrofite-painel-eletronico.webp",
        )
        self.assertMetaProperty(response, "og:image:width", "930")
        self.assertMetaProperty(response, "og:image:height", "470")
        self.assertMetaProperty(response, "og:image:alt", "Retrofit de painel eletrônico industrial")

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")
        services = self.graph_items(response, "Service")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Manutenção Industrial"],
        )
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(len(faq_pages[0]["mainEntity"]), 4)
        self.assertEqual(faq_pages[0]["mainEntity"][0]["name"], "Vocês fazem manutenção de robôs Xyron?")
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["name"], "Manutenção Industrial e Assistência Técnica em Campo")
        self.assertIn("Manutenção preventiva", services[0]["serviceType"])
        self.assertNotIn("areaServed", services[0])

    def test_strategic_solution_social_metadata_uses_existing_seo_values(self):
        expectations = (
            (
                "/xyron/?utm_source=google",
                "Robôs Inteligentes Xyron Robotics | Smart Control Brasil",
                "https://www.smartcontrolbrasil.com.br/xyron/",
            ),
            (
                "/mitsubishi-automacao-industrial/",
                "Automação Industrial Mitsubishi Electric | Smart Control Brasil",
                "https://www.smartcontrolbrasil.com.br/mitsubishi-automacao-industrial/",
            ),
        )

        for path, expected_title, expected_url in expectations:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertCanonical(response, expected_url)
                self.assertMetaProperty(response, "og:title", expected_title)
                self.assertMetaProperty(response, "og:url", expected_url)
                self.assertMetaProperty(response, "og:type", "website")
                self.assertMetaName(response, "twitter:title", expected_title)

    def test_xyron_hub_has_clean_links_semantic_cards_and_structured_data(self):
        response = self.client.get("/xyron/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Robôs Inteligentes Xyron Robotics | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Conheça as soluções de robótica inteligente da Xyron Robotics para educação, "
            "atendimento, interação e aplicações profissionais com a Smart Control Brasil.",
        )
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Xyron Robotics — Robótica Inteligente para Segurança, Educação e Empresas"],
        )

        for expected in (
            "Xyron Robotics",
            "robótica inteligente",
            "educação",
            "atendimento",
            "segurança",
            "serviços",
            "aplicações profissionais",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for forbidden in (
            'href="#"',
            "testimonials",
            "team_details",
            "blog_details",
            "Demosntração",
            "demo Images",
            "data-count",
            "Inscrever-se",
            "Digite seu e-mail",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        self.assertEqual(html.count('class="services-7__title"'), 12)
        self.assertEqual(html.count('<h3 class="services-7__title">'), 12)
        self.assertNotIn('<h2 class="services-7__title">', html)
        self.assertIn("Linha Xyron Robotics", html)

        for robot in XYRON_ROBOT_PAGES:
            with self.subTest(robot=robot["slug"]):
                self.assertIn(reverse(f"institutional:{robot['view']}"), html)

        self.assertIn(reverse("institutional:services"), html)
        self.assertIn(reverse("institutional:robotica_educacional"), html)
        self.assertIn(reverse("institutional:robos_limpeza_profissional"), html)
        self.assertIn(reverse("institutional:robos_seguranca_patrimonial"), html)
        self.assertIn(reverse("institutional:sistemas_websites_python"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(
            reverse(
                "institutional:blog_detail",
                kwargs={"slug": "convergencia-robotica-ia-firmwares-dedicados"},
            ),
            html,
        )

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")
        services = self.graph_items(response, "Service")
        item_lists = self.graph_items(response, "ItemList")
        products = self.graph_items(response, "Product")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics"],
        )
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(len(faq_pages[0]["mainEntity"]), 5)
        self.assertEqual(faq_pages[0]["mainEntity"][0]["name"], "Quais tipos de robôs a Xyron oferece?")
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["name"], "Soluções de Robótica Xyron Robotics")
        self.assertIn("Robótica educacional", services[0]["serviceType"])
        self.assertEqual(services[0]["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertNotIn("areaServed", services[0])
        self.assertEqual(len(item_lists), 1)
        self.assertEqual(len(item_lists[0]["itemListElement"]), len(XYRON_ROBOT_PAGES))
        self.assertEqual(
            [item["name"] for item in item_lists[0]["itemListElement"]],
            [robot["name"] for robot in XYRON_ROBOT_PAGES],
        )
        self.assertEqual(products, [])

    def test_xyron_robot_pages_include_product_schema_without_commercial_claims(self):
        for robot in XYRON_ROBOT_PAGES:
            path = f"/xyron/{robot['slug']}/"
            canonical = f"https://www.smartcontrolbrasil.com.br{path}"
            with self.subTest(path=path):
                response = self.client.get(path)
                products = self.graph_items(response, "Product")
                offers = self.graph_items(response, "Offer")
                aggregate_offers = self.graph_items(response, "AggregateOffer")
                reviews = self.graph_items(response, "Review")
                aggregate_ratings = self.graph_items(response, "AggregateRating")

                self.assertEqual(len(products), 1)
                product = products[0]
                self.assertEqual(product["name"], robot["name"])
                self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
                self.assertEqual(product["description"], robot["description"])
                self.assertEqual(product["url"], canonical)
                self.assertEqual(product["image"], f"https://www.smartcontrolbrasil.com.br{static(robot['image'])}")
                self.assertNotIn("offers", product)
                self.assertNotIn("aggregateRating", product)
                self.assertNotIn("review", product)
                self.assertEqual(offers, [])
                self.assertEqual(aggregate_offers, [])
                self.assertEqual(reviews, [])
                self.assertEqual(aggregate_ratings, [])

    def test_xyron_robot_pages_have_single_h1_metadata_breadcrumb_and_sitemap(self):
        sitemap_urls = self.sitemap_urls()

        for robot in XYRON_ROBOT_PAGES:
            path = f"/xyron/{robot['slug']}/"
            canonical = f"https://www.smartcontrolbrasil.com.br{path}"
            title = robot["title"]
            with self.subTest(path=path):
                response = self.client.get(f"{path}?utm_source=google")
                html = response.content.decode()

                self.assertEqual(response.status_code, 200)
                expected_h1 = robot["name"]
                if robot["key"] == "littlebot":
                    expected_h1 = "LIRO / Little Bot — Robô Interativo para Educação"
                elif robot["key"] == "orbit":
                    expected_h1 = "Orbit Bot / Patrol Bot — Robô de Patrulhamento e Segurança"
                elif robot["key"] == "neo_bot":
                    expected_h1 = "Neo Bot — Robô de Recepção e Atendimento"
                elif robot["key"] == "waiter_bot":
                    expected_h1 = "Waiter Bot — Robô de Entrega e Apoio Operacional"
                elif robot["key"] == "hygibot_dune_bot":
                    expected_h1 = "HygiBot / Dune Bot — Robô de Limpeza Autônoma"
                elif robot["key"] == "buddy_bot":
                    expected_h1 = "Buddy Bot — Robô Quadrúpede para Inspeção e Segurança"
                elif robot["key"] == "carebot":
                    expected_h1 = "CareBot — Robô Assistivo para Saúde e Atendimento"
                elif robot["key"] == "hostbot":
                    expected_h1 = "HostBot — Robô Host para Recepção e Eventos"
                elif robot["key"] == "mowerbot":
                    expected_h1 = "MowerBot — Robô Cortador de Grama para Áreas Externas"
                self.assertEqual(self.h1_texts(response), [expected_h1])
                self.assertTitle(response, title)
                self.assertMetaDescription(response, robot["description"])
                self.assertCanonical(response, canonical)
                self.assertNotContains(response, 'name="robots"')
                self.assertMetaProperty(response, "og:title", title)
                self.assertMetaProperty(response, "og:description", robot["description"])
                self.assertMetaProperty(response, "og:url", canonical)
                self.assertMetaProperty(response, "og:type", "website")
                expected_image_url = f"https://www.smartcontrolbrasil.com.br{static(robot['image'])}"
                self.assertMetaProperty(response, "og:image", expected_image_url)
                self.assertMetaName(response, "twitter:title", title)
                self.assertMetaName(response, "twitter:description", robot["description"])
                self.assertMetaName(response, "twitter:image", expected_image_url)
                self.assertIn(canonical, sitemap_urls)
                self.assertIn('fetchpriority="high"', html)
                self.assertIn(f'src="{static(robot["image"])}"', html)
                self.assertIn('href="/contato/"', html)

                breadcrumbs = self.graph_items(response, "BreadcrumbList")
                self.assertEqual(len(breadcrumbs), 1)
                items = breadcrumbs[0]["itemListElement"]
                self.assertEqual([item["name"] for item in items], ["Início", "Xyron Robotics", robot["name"]])
                self.assertEqual(items[1]["item"], "https://www.smartcontrolbrasil.com.br/xyron/")
                self.assertEqual(items[-1]["item"], canonical)





    def test_carebot_page_has_clean_copy_faq_schema_health_claims_and_contextual_links(self):
        response = self.client.get("/xyron/carebot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["carebot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/carebot/"
        old_meta_description = (
            "Robô assistivo para residências, clínicas, hospitais, farmácias e "
            "monitoramento inteligente de indicadores de saúde."
        )
        meta_description = (
            "CareBot é uma solução robótica assistiva para residências, clínicas, "
            "hospitais, farmácias e ambientes de saúde e atendimento."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "CareBot | Robô Assistivo para Saúde e Atendimento | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["CareBot — Robô Assistivo para Saúde e Atendimento"],
        )
        self.assertEqual(robot["name"], "CareBot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(old_meta_description, html)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "O card também cita",
            "O texto existente destaca",
            "A página apresenta",
            "Med Bot",
            "MedBot",
            "Medical Bot",
            "monitoramento inteligente de indicadores de saúde",
            "sinais vitais",
            "pressão arterial",
            "frequência cardíaca",
            "saturação",
            "glicemia",
            "ECG",
            "monitoramento clínico",
            "triagem",
            "prescrição",
            "tratamento",
            "telemedicina",
            "prontuário",
            "MedicalDevice",
            "ANVISA",
            "LGPD compliant",
            "dispositivo médico",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "robótica assistiva",
            "residências",
            "clínicas",
            "hospitais",
            "farmácias",
            "ambientes de saúde e atendimento",
            "O CareBot não substitui médicos",
            "privacidade",
            "responsabilidades",
            'href="/xyron/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/xyron/littlebot/"',
            'href="/xyron/neo-bot/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o CareBot?",
            "O CareBot substitui profissionais de saúde?",
            "Em quais tipos de ambiente o CareBot pode ser avaliado?",
            "O que deve ser considerado antes de implantar uma solução robótica em saúde?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        medical_devices = self.graph_items(response, "MedicalDevice")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "CareBot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "CareBot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("não substitui médicos", faq_entities[1]["acceptedAnswer"]["text"])
        self.assertIn("privacidade", faq_entities[3]["acceptedAnswer"]["text"])
        self.assertEqual(medical_devices, [])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])

    def test_hostbot_page_has_clean_copy_faq_schema_claims_and_contextual_links(self):
        response = self.client.get("/xyron/hostbot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["hostbot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/hostbot/"
        meta_description = (
            "Robô host com duas telas e inteligência artificial para recepção, "
            "eventos, empresas, museus, galerias e bancos."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "HostBot | Robô Host para Recepção e Eventos | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["HostBot — Robô Host para Recepção e Eventos"],
        )
        self.assertEqual(robot["name"], "HostBot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "conforme descrito no card",
            "landing institucional",
            "não substitui o commerce",
            "Connect Bot",
            "ConnectBot",
            "Host Bot",
            "check-in",
            "CRM",
            "reconhecimento facial",
            "biometria",
            "captura de leads",
            "sistema de filas",
            "touchscreen",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "robô host",
            "recepção",
            "eventos",
            "duas telas",
            "inteligência artificial",
            "comunicação visual",
            "empresas",
            "museus",
            "galerias",
            "bancos",
            "HostBot se diferencia pela função host",
            "Neo Bot",
            'href="/xyron/"',
            'href="/xyron/neo-bot/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o HostBot?",
            "Para quais tipos de ambiente o HostBot pode ser utilizado?",
            "Qual a diferença entre HostBot e Neo Bot?",
            "O que deve ser avaliado antes de implantar um robô de recepção ou eventos?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "HostBot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "HostBot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("duas telas", faq_entities[2]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])

    def test_buddy_bot_page_has_clean_copy_faq_schema_claims_and_contextual_links(self):
        response = self.client.get("/xyron/buddy-bot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["buddy_bot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/buddy-bot/"
        meta_description = (
            "Robô quadrúpede para inspeção, segurança patrimonial, engenharia, "
            "obras e áreas de difícil acesso."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Buddy Bot | Robô Quadrúpede para Inspeção e Segurança | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Buddy Bot — Robô Quadrúpede para Inspeção e Segurança"],
        )
        self.assertEqual(robot["name"], "Buddy Bot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "Nesta fase foram usados",
            "sem inventar especificações",
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "O conteúdo atual cita",
            "é apresentado como",
            "Budy Bot",
            "BuddyBot",
            "Robot Dog",
            "Spot",
            "cão robô",
            "sobe escadas",
            "terreno irregular",
            "câmera térmica",
            "LiDAR",
            "SLAM",
            "GPS",
            "detecção de gás",
            "teleoperação",
            "integração SCADA",
            "integração CFTV",
            "previne invasões",
            "substitui vigilantes",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "quadrúpede",
            "inspeção",
            "segurança patrimonial",
            "engenharia",
            "obras",
            "áreas de difícil acesso",
            "mobilidade",
            "sem substituir protocolos ou equipes",
            'href="/xyron/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/xyron/orbit/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o Buddy Bot?",
            "Em quais tipos de aplicação o Buddy Bot pode ser utilizado?",
            "Como um robô quadrúpede pode apoiar uma inspeção?",
            "O que deve ser avaliado antes de implantar um robô para inspeção?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "Buddy Bot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "Buddy Bot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("robô quadrúpede", faq_entities[0]["acceptedAnswer"]["text"])
        self.assertIn("superfície", faq_entities[3]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])

    def test_hygibot_dune_bot_page_has_clean_copy_faq_schema_claims_and_contextual_links(self):
        response = self.client.get("/xyron/hygibot-dune-bot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["hygibot_dune_bot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/hygibot-dune-bot/"
        meta_description = (
            "Robô autônomo que lava, varre, aspira e passa pano em shoppings, "
            "indústrias, hospitais e grandes áreas."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "HygiBot / Dune Bot | Robô de Limpeza Autônoma | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["HygiBot / Dune Bot — Robô de Limpeza Autônoma"],
        )
        self.assertEqual(robot["name"], "HygiBot / Dune Bot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "O conteúdo cita",
            "A página Xyron cita",
            "apresentado como",
            "Duno Bot",
            "Hygi Bot",
            "DuneBot",
            "desinfecção",
            "esterilização",
            "controle de infecção",
            "conformidade sanitária específica.",
            "centro cirúrgico",
            "SLAM",
            "LiDAR",
            "m²/h",
            "capacidade de tanque",
            "retorno automático à base",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "limpeza autônoma",
            "lavar",
            "varrer",
            "aspirar",
            "passar pano",
            "shoppings",
            "indústrias",
            "hospitais",
            "grandes áreas",
            "áreas compatíveis",
            "protocolos locais",
            "tipo de piso",
            "fluxo de pessoas",
            'href="/xyron/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/xyron/mowerbot/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o HygiBot / Dune Bot?",
            "Quais tipos de limpeza o HygiBot / Dune Bot pode realizar?",
            "Em quais ambientes ele pode ser utilizado?",
            "O que deve ser avaliado antes de implantar um robô de limpeza autônoma?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "HygiBot / Dune Bot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "HygiBot / Dune Bot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("lavar, varrer, aspirar e passar pano", faq_entities[1]["acceptedAnswer"]["text"])
        self.assertIn("protocolos locais", faq_entities[2]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])

    def test_waiter_bot_page_has_clean_copy_faq_schema_claims_and_contextual_links(self):
        response = self.client.get("/xyron/waiter-bot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["waiter_bot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/waiter-bot/"
        meta_description = (
            "Robô de entrega e apoio operacional para restaurantes, hotéis, "
            "supermercados e ambientes de atendimento."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Waiter Bot | Robô de Entrega e Apoio Operacional | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Waiter Bot — Robô de Entrega e Apoio Operacional"],
        )
        self.assertEqual(robot["name"], "Waiter Bot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "página Xyron",
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "landing institucional",
            "commerce",
            "não há imagem real específica",
            "Existe imagem específica no projeto",
            "Aplicação indicada",
            "Benefícios coerentes",
            "room service",
            "capacidade de carga",
            "integração com PDV",
            "integração com cozinha",
            "recebe pedidos",
            "substitui garçom",
            "Robô Garçom",
            "Relay Bot",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "entrega",
            "apoio operacional",
            "restaurantes",
            "hotéis",
            "supermercados",
            "ambientes de atendimento",
            "transporte de itens",
            "sem substituir a equipe",
            'href="/xyron/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o Waiter Bot?",
            "Em quais ambientes o Waiter Bot pode ser utilizado?",
            "Como um robô de entrega pode apoiar uma operação de atendimento?",
            "O que deve ser avaliado antes de implantar um Waiter Bot?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "Waiter Bot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "Waiter Bot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("entregas internas", faq_entities[0]["acceptedAnswer"]["text"])
        self.assertIn("sem substituir a equipe", faq_entities[2]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])

    def test_neo_bot_page_has_clean_copy_faq_schema_claims_and_contextual_links(self):
        response = self.client.get("/xyron/neo-bot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["neo_bot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/neo-bot/"
        old_meta_description = (
            "Robô de recepção e atendimento com diálogo multilíngue, IA, "
            "reconhecimento facial e apresentação de produtos."
        )
        meta_description = (
            "Robô de recepção e atendimento com diálogo multilíngue, IA e apoio "
            "à apresentação de produtos em experiências corporativas."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Neo Bot | Robô de Recepção e Atendimento | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Neo Bot — Robô de Recepção e Atendimento"],
        )
        self.assertEqual(robot["name"], "Neo Bot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(old_meta_description, html)
        self.assertNotIn(meta_description, body)
        self.assertNotIn("reconhecimento facial", html.lower())

        for forbidden in (
            "página Xyron",
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "landing institucional",
            "commerce permanece separado",
            "Aplicação indicada",
            "Benefícios coerentes",
            "CRM",
            "ERP",
            "check-in automático",
            "controle de acesso",
            "leitor QR Code",
            "NFC",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "recepção",
            "atendimento",
            "diálogo multilíngue",
            "IA",
            "apresentação de produtos",
            "experiência do visitante",
            "sem substituir a equipe",
            'href="/xyron/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/xyron/hostbot/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o Neo Bot?",
            "Em quais ambientes o Neo Bot pode ser usado?",
            "Como o Neo Bot pode apoiar uma recepção?",
            "O Neo Bot pode ser integrado a um projeto de atendimento?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "Neo Bot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "Neo Bot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("diálogo multilíngue", faq_entities[0]["acceptedAnswer"]["text"])
        self.assertIn("sem substituir a equipe", faq_entities[2]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])


    def test_mowerbot_page_has_clean_copy_faq_schema_claims_and_contextual_links(self):
        response = self.client.get("/xyron/mowerbot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["mowerbot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/mowerbot/"
        meta_description = (
            "Robô cortador de grama por controle remoto para terrenos irregulares, "
            "taludes, praças e grandes áreas externas."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "MowerBot | Robô Cortador de Grama para Áreas Externas | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["MowerBot — Robô Cortador de Grama para Áreas Externas"],
        )
        self.assertEqual(robot["name"], "MowerBot")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "card da página Xyron",
            "conteúdo Xyron",
            "extraídas dos textos existentes",
            "O card cita",
            "O card apresenta",
            "Existe imagem específica no projeto",
            "não há imagem real específica",
            "página informa preço",
            "venda direta",
            "autônomo de jardim",
            "opera sozinho",
            "navegação autônoma",
            "inclinação máxima",
            "largura de corte",
            "hectares/h",
            "m²/h",
            "retorno automático",
            "GPS",
            "RTK",
            "LiDAR",
            "SLAM",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "corte de grama",
            "controle remoto",
            "terrenos irregulares",
            "taludes",
            "praças",
            "grandes áreas externas",
            "operação remota",
            "não deve ser tratada como promessa de operação autônoma",
            'href="/xyron/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/xyron/hygibot-dune-bot/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o MowerBot?",
            "O MowerBot é autônomo ou operado por controle remoto?",
            "Em quais tipos de terreno o MowerBot pode ser avaliado?",
            "O que deve ser avaliado antes de utilizar um robô cortador de grama?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "MowerBot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "MowerBot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("controle remoto", faq_entities[1]["acceptedAnswer"]["text"])
        self.assertIn("não deve ser tratada como promessa de operação autônoma", faq_entities[1]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])


    def test_orbit_page_has_clean_copy_faq_schema_and_contextual_links(self):
        response = self.client.get("/xyron/orbit/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        body = html.split("<body", 1)[1]
        robot = XYRON_ROBOT_PAGE_BY_KEY["orbit"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/orbit/"
        meta_description = (
            "Robô de patrulhamento e segurança para grandes áreas, com navegação autônoma, "
            "visão inteligente e monitoramento em tempo real."
        )

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Orbit Bot | Robô de Patrulhamento e Segurança | Smart Control Brasil")
        self.assertMetaDescription(response, meta_description)
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Orbit Bot / Patrol Bot — Robô de Patrulhamento e Segurança"],
        )
        self.assertEqual(robot["name"], "Orbit Bot / Patrol Bot")
        self.assertEqual(robot["title"], "Orbit Bot | Robô de Patrulhamento e Segurança | Smart Control Brasil")
        self.assertEqual(robot["description"], meta_description)
        self.assertNotIn(meta_description, body)

        for forbidden in (
            "card da página Xyron",
            "conteúdo Xyron",
            "Aplicação indicada no conteúdo",
            "O conteúdo atual indica",
            "A página apresenta o Orbit",
            "Benefícios coerentes",
            "substitui vigilantes",
            "garante segurança",
            "reconhecimento facial",
            "câmera térmica",
            "LiDAR",
            "SLAM",
            "GPS",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

        for expected in (
            "Xyron Robotics",
            "patrulhamento",
            "monitoramento",
            "grandes áreas",
            "navegação autônoma",
            "visão inteligente",
            "monitoramento em tempo real",
            "condomínios",
            "empresas",
            "áreas corporativas",
            "não como substituto",
            'href="/xyron/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o Orbit Bot / Patrol Bot?",
            "Onde o Orbit pode ser aplicado?",
            "O Orbit substitui uma equipe de segurança?",
            "Como avaliar uma aplicação do Orbit?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "Orbit Bot / Patrol Bot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "Orbit Bot / Patrol Bot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], meta_description)
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("deslocamento autônomo", faq_entities[0]["acceptedAnswer"]["text"])
        self.assertIn("não como substituto", faq_entities[2]["acceptedAnswer"]["text"].lower())
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])


    def test_littlebot_page_has_faq_schema_consistent_naming_and_contextual_links(self):
        response = self.client.get("/xyron/littlebot/?utm_source=google&utm_campaign=x")
        html = response.content.decode()
        robot = XYRON_ROBOT_PAGE_BY_KEY["littlebot"]
        canonical = "https://www.smartcontrolbrasil.com.br/xyron/littlebot/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "LIRO / Little Bot | Robô Educacional Interativo | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Conheça o LIRO / Little Bot, robô interativo para educação, experiências STEM, "
            "demonstrações e ambientes de aprendizagem e tecnologia.",
        )
        self.assertCanonical(response, canonical)
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["LIRO / Little Bot — Robô Interativo para Educação"],
        )
        self.assertEqual(robot["name"], "LIRO / Little Bot")
        self.assertEqual(robot["title"], "LIRO / Little Bot | Robô Educacional Interativo | Smart Control Brasil")
        self.assertNotIn("clínicas", robot["description"].lower())
        self.assertNotIn("creches", robot["description"].lower())
        self.assertNotIn("atendimento especializado", robot["description"].lower())

        for expected in (
            "robô interativo",
            "robótica educacional",
            "experiências STEM",
            "educação",
            "tecnologia",
            "interação",
            'href="/xyron/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/contato/"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        faq_questions = [
            "O que é o LIRO / Little Bot?",
            "O LIRO / Little Bot pode ser utilizado em escolas?",
            "É possível realizar uma demonstração?",
            "Como posso levar o LIRO / Little Bot para minha instituição?",
        ]
        for question in faq_questions:
            with self.subTest(question=question):
                self.assertIn(question, html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        products = self.graph_items(response, "Product")
        faq_pages = self.graph_items(response, "FAQPage")
        offers = self.graph_items(response, "Offer")
        aggregate_ratings = self.graph_items(response, "AggregateRating")
        reviews = self.graph_items(response, "Review")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Xyron Robotics", "LIRO / Little Bot"],
        )
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["name"], "LIRO / Little Bot")
        self.assertEqual(product["brand"], {"@type": "Brand", "name": "Xyron Robotics"})
        self.assertEqual(product["description"], robot["description"])
        self.assertEqual(product["url"], canonical)
        self.assertNotIn("offers", product)
        self.assertNotIn("aggregateRating", product)
        self.assertNotIn("review", product)

        self.assertEqual(len(faq_pages), 1)
        faq_entities = faq_pages[0]["mainEntity"]
        self.assertEqual([item["name"] for item in faq_entities], faq_questions)
        self.assertIn("experiências envolvendo robótica", faq_entities[0]["acceptedAnswer"]["text"])
        self.assertIn("experiências STEM", faq_entities[1]["acceptedAnswer"]["text"])
        self.assertEqual(offers, [])
        self.assertEqual(aggregate_ratings, [])
        self.assertEqual(reviews, [])


    def test_internal_links_connect_home_xyron_pages_blog_and_contact(self):
        home = self.client.get("/")
        xyron = self.client.get("/xyron/")
        manutencao = self.client.get("/manutencao-industrial-campo/")
        blog = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")

        self.assertContains(home, 'href="/mitsubishi-automacao-industrial/"')
        self.assertContains(home, 'href="/xyron/"')
        self.assertContains(home, 'href="/robos-de-seguranca-patrimonial/"')
        self.assertContains(home, 'href="/sistemas-websites-python/"')
        for robot in XYRON_ROBOT_PAGES:
            self.assertContains(xyron, f'href="/xyron/{robot["slug"]}/"')
        self.assertContains(xyron, 'href="/robotica-educacional/"')
        self.assertContains(xyron, 'href="/robos-de-limpeza-profissional/"')
        self.assertContains(xyron, 'href="/robos-de-seguranca-patrimonial/"')
        self.assertNotContains(xyron, 'href="/robo-seguranca-condominios/"')
        self.assertNotContains(manutencao, 'href="/camara-climatica/"')
        self.assertContains(blog, 'href="/mitsubishi-automacao-industrial/"')
        self.assertContains(blog, 'href="/contato/"')

    def test_blog_hub_has_descriptive_h1_breadcrumb_blog_schema_and_item_list(self):
        response = self.client.get("/blog/?utm_source=google&utm_campaign=x")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Blog de Automação Industrial, Robótica e Tecnologia | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Artigos técnicos sobre automação industrial, robótica, manutenção, "
            "integração de dados, sistemas web e engenharia aplicada.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/blog/")
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(
            self.h1_texts(response),
            ["Blog de Automação Industrial, Robótica e Tecnologia"],
        )
        self.assertNotIn("fa-calendar-days", html)
        self.assertIn("fa-tags", html)

        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        blogs = self.graph_items(response, "Blog")
        item_lists = self.graph_items(response, "ItemList")

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(
            [item["name"] for item in breadcrumbs[0]["itemListElement"]],
            ["Início", "Blog"],
        )
        self.assertEqual(len(blogs), 1)
        self.assertEqual(blogs[0]["url"], "https://www.smartcontrolbrasil.com.br/blog/")
        self.assertEqual(blogs[0]["publisher"]["name"], "Smart Control Brasil")
        self.assertEqual(len(item_lists), 1)
        self.assertEqual(len(item_lists[0]["itemListElement"]), len(BLOG_POSTS))
        self.assertEqual(
            [item["name"] for item in item_lists[0]["itemListElement"]],
            [post["title"] for post in BLOG_POSTS.values()],
        )

    def test_blog_articles_use_blogposting_schema_links_highlights_and_related_posts(self):
        landing_paths = {
            "selecao-controladores-ativos-alta-severidade": reverse("institutional:mitsubishi_automacao_industrial"),
            "convergencia-robotica-ia-firmwares-dedicados": reverse("institutional:xyron"),
            "eliminar-gargalos-autonomia-previsibilidade": reverse("institutional:manutencao_industrial_campo"),
            "informacao-precisa-para-agir-melhor": reverse("institutional:sistemas_websites_python"),
            "equipamentos-sistemas-para-evoluir": reverse("institutional:sistemas_websites_python"),
            "inovacao-que-aparece-e-gera-valor": reverse("institutional:xyron"),
            "reducao-paradas-inesperadas-planejamento-tecnico": reverse("institutional:manutencao_industrial_campo"),
            "historico-indicadores-decisoes-consistentes": reverse("institutional:manutencao_industrial_campo"),
            "menos-retrabalho-rastreabilidade-retrofit": reverse("institutional:manutencao_industrial_campo"),
        }
        highlights = []

        for slug, post in BLOG_POSTS.items():
            path = f"/blog/{slug}/"
            canonical = f"https://www.smartcontrolbrasil.com.br{path}"
            with self.subTest(slug=slug):
                response = self.client.get(path)
                html = response.content.decode()

                self.assertEqual(response.status_code, 200)
                self.assertTitle(response, post.get("seo_title") or f"{post['title']} | Smart Control Brasil")
                self.assertMetaDescription(response, post["meta_description"])
                self.assertCanonical(response, canonical)
                self.assertEqual(self.h1_texts(response), [post["title"]])
                self.assertIn(f'src="{static(post["image"])}"', html)
                self.assertIn(post["highlight"], html)
                self.assertIn(landing_paths[slug], html)
                self.assertNotIn(reverse("institutional:blog_details"), html)
                self.assertNotIn(reverse("institutional:blog_list"), html)
                highlights.append(post["highlight"])

                blog_posts = self.graph_items(response, "BlogPosting")
                articles = self.graph_items(response, "Article")
                breadcrumbs = self.graph_items(response, "BreadcrumbList")

                self.assertEqual(articles, [])
                self.assertEqual(len(blog_posts), 1)
                blog_posting = blog_posts[0]
                self.assertEqual(blog_posting["headline"], post["title"])
                self.assertEqual(blog_posting["description"], post["meta_description"])
                self.assertEqual(blog_posting["url"], canonical)
                self.assertEqual(blog_posting["mainEntityOfPage"], canonical)
                self.assertEqual(blog_posting["articleSection"], post["category"])
                self.assertEqual(blog_posting["image"], f"https://www.smartcontrolbrasil.com.br/static/{post['image']}")
                self.assertBlogPostingAuthorAndDates(blog_posting, slug)
                self.assertEqual(len(breadcrumbs), 1)
                self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])

                related_hrefs = re.findall(r'class="sidebar-post_thumb" href="([^"]+)"|href="([^"]+)" class="sidebar-post_thumb"', html)
                related_urls = {first or second for first, second in related_hrefs}
                self.assertLessEqual(len(related_urls), 3)
                self.assertNotIn(path, related_urls)

        self.assertEqual(len(set(highlights)), len(BLOG_POSTS))

    def test_blog_detail_does_not_render_python_dict_artifacts_and_keeps_legitimate_lists(self):
        for slug in BLOG_POSTS:
            with self.subTest(slug=slug):
                response = self.client.get(f"/blog/{slug}/")
                html = response.content.decode()

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("('heading',", html)
                self.assertNotIn("('paragraphs',", html)
                self.assertNotIn("dict_items", html)

        checklist = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        self.assertContains(checklist, "<li>Ambiente de instalação e exposição real do equipamento.</li>")

    def test_robotics_ai_firmware_article_has_expanded_depth_links_and_faq_schema(self):
        response = self.client.get("/blog/convergencia-robotica-ia-firmwares-dedicados/")
        html = response.content.decode()
        post = BLOG_POSTS["convergencia-robotica-ia-firmwares-dedicados"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/convergencia-robotica-ia-firmwares-dedicados/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Robótica, IA e Firmware Dedicado | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "A arquitetura de um sistema robótico moderno",
            "Firmware dedicado: a camada que conversa com o hardware",
            "Por que processamento local importa",
            "Inteligência artificial na robótica",
            "Visão computacional e sensores",
            "Comunicação entre robô e sistemas externos",
            "Robótica conectada não significa dependência total da nuvem",
            "Onde a Xyron Robotics entra nesse cenário",
            "Aplicações práticas da convergência",
            "Exemplo arquitetural hipotético",
            "Segurança, disponibilidade e confiabilidade",
            "Integração precisa nascer da aplicação",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "firmware",
            "inteligência artificial",
            "sensores",
            "processamento local",
            "integração",
            "Xyron Robotics",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/xyron/"',
            'href="/xyron/littlebot/"',
            'href="/xyron/orbit/"',
            'href="/xyron/neo-bot/"',
            'href="/sistemas-websites-python/"',
            'href="/blog/inovacao-que-aparece-e-gera-valor/"',
            'href="/servicos/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("Esse exemplo é hipotético", html)
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Automação Industrial e Transformação Digital")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "convergencia-robotica-ia-firmwares-dedicados")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

    def test_robotics_value_article_has_expanded_depth_links_cta_and_faq_schema(self):
        response = self.client.get("/blog/inovacao-que-aparece-e-gera-valor/")
        html = response.content.decode()
        post = BLOG_POSTS["inovacao-que-aparece-e-gera-valor"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/inovacao-que-aparece-e-gera-valor/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Robótica Aplicada e Valor Operacional | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "Comece pelo problema, não pelo robô",
            "Onde a robótica aplicada pode gerar valor",
            "Xyron Robotics como ecossistema de aplicações",
            "Integração com o processo existente",
            "Tecnologia visível precisa ter função clara",
            "Experiência do usuário faz parte do resultado",
            "Como medir se a aplicação gera valor",
            "ROI e TCO não contam a história inteira",
            "Projeto piloto reduz incerteza",
            "Exemplo hipotético",
            "Quando a robótica não é a melhor resposta",
            "Robótica aplicada e arquitetura técnica são temas complementares",
            "Checklist para avaliar uma aplicação de robótica",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "robótica aplicada",
            "valor operacional",
            "indicadores",
            "implantação",
            "integração",
            "baseline",
            "ROI",
            "TCO",
            "Projeto piloto",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/xyron/"',
            'href="/xyron/littlebot/"',
            'href="/xyron/neo-bot/"',
            'href="/xyron/orbit/"',
            'href="/xyron/hygibot-dune-bot/"',
            'href="/xyron/buddy-bot/"',
            'href="/xyron/carebot/"',
            'href="/xyron/hostbot/"',
            'href="/sistemas-websites-python/"',
            'href="/blog/convergencia-robotica-ia-firmwares-dedicados/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("linha de robôs Xyron Robotics", html)
        self.assertIn("Considere uma empresa", html)
        self.assertContains(response, "<li>Qual problema queremos resolver?</li>")
        self.assertContains(response, "Conversar sobre uma aplicação de robótica")
        self.assertNotIn("Conhecer soluções robóticas", html)
        self.assertNotIn("processamento local", html)
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Robótica Aplicada")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "inovacao-que-aparece-e-gera-valor")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        xyron = self.client.get("/xyron/")
        self.assertEqual(xyron.status_code, 200)
        self.assertContains(xyron, 'href="/blog/inovacao-que-aparece-e-gera-valor/"')

    def test_operational_bottlenecks_article_has_expanded_depth_links_and_faq_schema(self):
        response = self.client.get("/blog/eliminar-gargalos-autonomia-previsibilidade/")
        html = response.content.decode()
        post = BLOG_POSTS["eliminar-gargalos-autonomia-previsibilidade"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/eliminar-gargalos-autonomia-previsibilidade/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Gargalos Operacionais: Como Identificar e Reduzir")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "O que é um gargalo operacional",
            "Comece pelo fluxo, não pela máquina",
            "Como identificar o verdadeiro gargalo",
            "Indicadores que ajudam a localizar perdas",
            "Manutenção pode ser causa ou consequência do gargalo",
            "Quando automação ajuda a reduzir gargalos",
            "Padronização antes de automatização",
            "Capacidade e restrição precisam ser analisadas juntas",
            "Setup e mudanças frequentes",
            "Dados transformam reação em previsibilidade",
            "Checklist para investigar um gargalo",
            "Exemplo hipotético: uma linha com três etapas",
            "Melhorar o gargalo pode deslocá-lo",
            "Da reação para uma operação previsível",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "gargalo operacional",
            "tempo de ciclo",
            "disponibilidade",
            "MTBF",
            "MTTR",
            "automação",
            "manutenção",
            "previsibilidade",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/manutencao-industrial-campo/"',
            'href="/blog/reducao-paradas-inesperadas-planejamento-tecnico/"',
            'href="/blog/historico-indicadores-decisoes-consistentes/"',
            'href="/sistemas-websites-python/"',
            'href="/mitsubishi-automacao-industrial/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("autonomia operacional significa", html)
        self.assertIn("Não se trata de robôs autônomos", html)
        self.assertIn("Mapeamento do Fluxo de Valor", html)
        self.assertIn("Teoria das Restrições", html)
        self.assertIn("SMED", html)
        self.assertIn("Considere uma linha fictícia", html)
        self.assertContains(response, "<li>Onde a fila se forma e por quanto tempo ela permanece?</li>")
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Eficiência Operacional")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "eliminar-gargalos-autonomia-previsibilidade")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        maintenance = self.client.get("/manutencao-industrial-campo/")
        maintenance_html = maintenance.content.decode()
        self.assertEqual(maintenance.status_code, 200)
        self.assertIn('href="/blog/eliminar-gargalos-autonomia-previsibilidade/"', maintenance_html)
        self.assertIn('href="/blog/historico-indicadores-decisoes-consistentes/"', maintenance_html)

    def test_asset_history_indicators_article_has_expanded_depth_links_and_faq_schema(self):
        response = self.client.get("/blog/historico-indicadores-decisoes-consistentes/")
        html = response.content.decode()
        post = BLOG_POSTS["historico-indicadores-decisoes-consistentes"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/historico-indicadores-decisoes-consistentes/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Gestão de Ativos: Histórico e Indicadores para Decisão | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "O que um histórico de manutenção precisa responder",
            "O que registrar em uma ordem de serviço",
            "Padronização dos registros",
            "Indicadores devem responder perguntas",
            "MTBF e MTTR no contexto do ativo",
            "Backlog, custos e recorrência",
            "Indicadores sem contexto podem enganar",
            "Histórico ajuda a separar sintoma de padrão",
            "Criticidade precisa entrar na análise",
            "CMMS, sistemas e dados",
            "Reparar, modernizar ou substituir?",
            "TCO na gestão do ativo",
            "Matriz textual de decisão",
            "Exemplo hipotético",
            "Checklist para organizar histórico e indicadores",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "ordem de serviço",
            "histórico",
            "MTBF",
            "MTTR",
            "backlog",
            "criticidade",
            "gestão de ativos",
            "modernizar",
            "CMMS",
            "TCO",
            "recorrência",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/manutencao-industrial-campo/"',
            'href="/blog/reducao-paradas-inesperadas-planejamento-tecnico/"',
            'href="/blog/eliminar-gargalos-autonomia-previsibilidade/"',
            'href="/blog/informacao-precisa-para-agir-melhor/"',
            'href="/sistemas-websites-python/"',
            'href="/blog/equipamentos-sistemas-para-evoluir/"',
            'href="/blog/menos-retrabalho-rastreabilidade-retrofit/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("MTBF = tempo de operação / número de falhas", html)
        self.assertIn("MTTR = tempo total de reparo / quantidade de reparos", html)
        self.assertIn("Esse exemplo é hipotético", html)
        self.assertContains(response, "<li>Ativos estão identificados de forma única?</li>")
        self.assertContains(response, "Estruturar gestão de ativos")
        self.assertNotIn("ROI", html)
        self.assertNotIn("disponibilidade alcançada", html)
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Gestão de Ativos")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "historico-indicadores-decisoes-consistentes")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        maintenance = self.client.get("/manutencao-industrial-campo/")
        maintenance_html = maintenance.content.decode()
        self.assertEqual(maintenance.status_code, 200)
        self.assertIn('href="/blog/historico-indicadores-decisoes-consistentes/"', maintenance_html)
        self.assertIn('alt="Histórico e indicadores de manutenção para gestão de ativos"', maintenance_html)

    def test_unplanned_stops_article_has_expanded_depth_links_and_faq_schema(self):
        response = self.client.get("/blog/reducao-paradas-inesperadas-planejamento-tecnico/")
        html = response.content.decode()
        post = BLOG_POSTS["reducao-paradas-inesperadas-planejamento-tecnico"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/reducao-paradas-inesperadas-planejamento-tecnico/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Redução de Paradas e Planejamento de Manutenção | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "Parada inesperada não é apenas falha de equipamento",
            "Corretiva, preventiva e preditiva têm papéis diferentes",
            "Criticidade define prioridade",
            "Histórico de falhas é uma das melhores fontes de decisão",
            "MTBF: frequência entre falhas",
            "MTTR: capacidade de restaurar o equipamento",
            "MTBF e MTTR devem ser analisados juntos",
            "Planejamento e programação de manutenção",
            "Ordem de serviço precisa gerar informação",
            "Pequenas paradas também importam",
            "Quando automação participa da solução",
            "Sistemas e dados ajudam a sair da manutenção reativa",
            "TPM, RCM e modos de falha como apoio",
            "Exemplo hipotético",
            "Plano de ação deve atacar causa e recorrência",
            "Checklist para reduzir paradas inesperadas",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "MTBF",
            "MTTR",
            "criticidade",
            "manutenção preventiva",
            "preditiva",
            "planejamento",
            "programação",
            "confiabilidade",
            "disponibilidade",
            "TPM",
            "RCM",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "MTBF = tempo de operação / número de falhas",
            "MTTR = tempo total de reparo / número de reparos",
            "disponibilidade ≈ MTBF / (MTBF + MTTR)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/manutencao-industrial-campo/"',
            'href="/blog/eliminar-gargalos-autonomia-previsibilidade/"',
            'href="/blog/historico-indicadores-decisoes-consistentes/"',
            'href="/sistemas-websites-python/"',
            'href="/blog/informacao-precisa-para-agir-melhor/"',
            'href="/mitsubishi-automacao-industrial/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("Esse exemplo é hipotético", html)
        self.assertContains(response, "<li>Quais ativos são críticos?</li>")
        self.assertContains(response, "Solicitar diagnóstico de manutenção")
        self.assertNotIn("reduz custos em", html)
        self.assertNotIn("retorno em", html)
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Engenharia de Manutenção")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "reducao-paradas-inesperadas-planejamento-tecnico")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        maintenance = self.client.get("/manutencao-industrial-campo/")
        maintenance_html = maintenance.content.decode()
        self.assertEqual(maintenance.status_code, 200)
        self.assertIn('href="/blog/reducao-paradas-inesperadas-planejamento-tecnico/"', maintenance_html)
        self.assertIn('alt="Planejamento de manutenção industrial para redução de paradas"', maintenance_html)

    def test_rework_traceability_retrofit_article_has_expanded_depth_links_carousel_and_faq_schema(self):
        response = self.client.get("/blog/menos-retrabalho-rastreabilidade-retrofit/")
        html = response.content.decode()
        post = BLOG_POSTS["menos-retrabalho-rastreabilidade-retrofit"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/menos-retrabalho-rastreabilidade-retrofit/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Retrofit Industrial: Documentação, Backup e Rastreabilidade | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "O que é retrabalho técnico",
            "Levantamento técnico antes de alterar",
            "Documentação as-built",
            "Lista de I/O e sinais de campo",
            "Backup de CLP e IHM",
            "Versionamento de software e parâmetros",
            "Rastreabilidade das alterações",
            "Documentação e paradas inesperadas",
            "Quando o levantamento revela necessidade de modernização",
            "Retrofit por etapas",
            "Integração de dados também precisa ser documentada",
            "Exemplo hipotético",
            "Checklist antes de iniciar um retrofit",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "retrofit",
            "rastreabilidade",
            "backup",
            "CLP",
            "IHM",
            "as-built",
            "levantamento técnico",
            "versionamento",
            "parâmetros",
            "I/O list",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/manutencao-industrial-campo/"',
            'href="/mitsubishi-automacao-industrial/"',
            'href="/blog/historico-indicadores-decisoes-consistentes/"',
            'href="/blog/reducao-paradas-inesperadas-planejamento-tecnico/"',
            'href="/blog/equipamentos-sistemas-para-evoluir/"',
            'href="/blog/selecao-controladores-ativos-alta-severidade/"',
            'href="/sistemas-websites-python/"',
            'href="/blog/informacao-precisa-para-agir-melhor/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("Esse exemplo é hipotético", html)
        self.assertContains(response, "<li>Equipamento está corretamente identificado?</li>")
        self.assertContains(response, "Solicitar levantamento técnico e retrofit")
        self.assertNotIn("NR-10", html)
        self.assertNotIn("redução percentual", html)
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Retrofit Industrial")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "menos-retrabalho-rastreabilidade-retrofit")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        maintenance = self.client.get("/manutencao-industrial-campo/")
        maintenance_html = maintenance.content.decode()
        self.assertEqual(maintenance.status_code, 200)
        self.assertIn('href="/blog/menos-retrabalho-rastreabilidade-retrofit/"', maintenance_html)
        self.assertIn('alt="Documentação e rastreabilidade para retrofit industrial"', maintenance_html)
        self.assertIn('href="/contato/" class="learn-btn">Solicitar visita', maintenance_html)
        self.assertNotIn(
            '<h5 class="title"><a href="/contato/">Menos retrabalho, mais rastreabilidade e base para retrofit</a></h5>',
            maintenance_html,
        )

    def test_industrial_data_article_has_expanded_depth_links_and_faq_schema(self):
        response = self.client.get("/blog/informacao-precisa-para-agir-melhor/")
        html = response.content.decode()
        post = BLOG_POSTS["informacao-precisa-para-agir-melhor"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/informacao-precisa-para-agir-melhor/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Dados Industriais: Da Coleta à Decisão Operacional")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "De onde vêm os dados industriais",
            "Coletar não basta: é preciso contextualizar",
            "Arquitetura do fluxo de informação",
            "Integração entre OT e sistemas digitais",
            "APIs como ponte entre sistemas",
            "Banco de dados e histórico",
            "Dashboards diferentes para usuários diferentes",
            "Alarmes úteis versus excesso de alarmes",
            "Evento, alarme e indicador não são a mesma coisa",
            "Rastreabilidade",
            "Da reação para a decisão baseada em evidências",
            "Inteligência artificial entra depois da base de dados",
            "Exemplo hipotético",
            "Checklist para transformar dados em informação útil",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "dados industriais",
            "CLP",
            "dashboard",
            "APIs",
            "Python",
            "Django",
            "rastreabilidade",
            "histórico",
            "indicadores",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/sistemas-websites-python/"',
            'href="/mitsubishi-automacao-industrial/"',
            'href="/manutencao-industrial-campo/"',
            'href="/blog/historico-indicadores-decisoes-consistentes/"',
            'href="/blog/menos-retrabalho-rastreabilidade-retrofit/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("Dado não é informação", html)
        self.assertIn("Esse exemplo é hipotético", html)
        self.assertContains(response, "<li>Qual decisão precisa ser tomada com essa informação?</li>")
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Integração Inteligente")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "informacao-precisa-para-agir-melhor")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        systems = self.client.get("/sistemas-websites-python/")
        self.assertEqual(systems.status_code, 200)
        self.assertContains(systems, 'href="/blog/informacao-precisa-para-agir-melhor/"')
        self.assertContains(systems, 'href="/blog/equipamentos-sistemas-para-evoluir/"')

    def test_equipment_systems_modernization_article_has_expanded_depth_links_and_faq_schema(self):
        response = self.client.get("/blog/equipamentos-sistemas-para-evoluir/")
        html = response.content.decode()
        post = BLOG_POSTS["equipamentos-sistemas-para-evoluir"]
        canonical = "https://www.smartcontrolbrasil.com.br/blog/equipamentos-sistemas-para-evoluir/"

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Retrofit e Modernização Industrial | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(response, canonical)
        self.assertEqual(self.h1_texts(response), [post["title"]])
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotContains(response, 'name="robots"')

        expected_sections = (
            "O primeiro passo é entender por que modernizar",
            "Retrofit ou substituição completa?",
            "Matriz de decisão para modernização",
            "Obsolescência não é apenas idade",
            "Controle e automação na modernização",
            "Manutenção deve participar da decisão",
            "Modernizar equipamento sem modernizar informação pode limitar o resultado",
            "Integração deve ser planejada para o ciclo de vida",
            "TCO: olhar além do preço de compra",
            "Payback não deve ser analisado isoladamente",
            "Exemplo hipotético",
            "Modernização em etapas",
            "Checklist para avaliar uma modernização",
        )
        for expected in expected_sections:
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected in (
            "modernização",
            "retrofit",
            "obsolescência",
            "ciclo de vida",
            "TCO",
            "automação",
            "integração",
            "manutenção",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

        for expected_href in (
            'href="/manutencao-industrial-campo/"',
            'href="/mitsubishi-automacao-industrial/"',
            'href="/sistemas-websites-python/"',
            'href="/blog/informacao-precisa-para-agir-melhor/"',
            'href="/blog/selecao-controladores-ativos-alta-severidade/"',
            'href="/blog/menos-retrabalho-rastreabilidade-retrofit/"',
            'href="/contato/"',
        ):
            with self.subTest(expected_href=expected_href):
                self.assertIn(expected_href, html)

        self.assertIn("Considere uma máquina", html)
        self.assertContains(response, "<li>Qual problema motiva a mudança?</li>")
        self.assertNotIn("('heading',", html)
        self.assertNotIn("('paragraphs',", html)
        self.assertNotIn("dict_items", html)

        blog_postings = self.graph_items(response, "BlogPosting")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")
        faq_pages = self.graph_items(response, "FAQPage")

        self.assertEqual(len(blog_postings), 1)
        self.assertEqual(blog_postings[0]["headline"], post["title"])
        self.assertEqual(blog_postings[0]["description"], post["meta_description"])
        self.assertEqual(blog_postings[0]["url"], canonical)
        self.assertEqual(blog_postings[0]["mainEntityOfPage"], canonical)
        self.assertEqual(blog_postings[0]["articleSection"], "Soluções Tecnológicas")
        self.assertBlogPostingAuthorAndDates(blog_postings[0], "equipamentos-sistemas-para-evoluir")
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual([item["name"] for item in breadcrumbs[0]["itemListElement"]][:2], ["Início", "Blog"])
        self.assertEqual(len(faq_pages), 1)
        self.assertEqual(
            [item["name"] for item in faq_pages[0]["mainEntity"]],
            [item["question"] for item in post["faq"]],
        )
        self.assertEqual(
            [item["acceptedAnswer"]["text"] for item in faq_pages[0]["mainEntity"]],
            [item["answer"] for item in post["faq"]],
        )

        systems = self.client.get("/sistemas-websites-python/")
        systems_html = systems.content.decode()
        self.assertEqual(systems.status_code, 200)
        self.assertContains(systems, 'href="/blog/equipamentos-sistemas-para-evoluir/"')
        self.assertIn("Modernização de Equipamentos", systems_html)
        self.assertNotIn("Inteligência artificial integrada <br> aos seus sistemas e dados", systems_html)

    def test_legacy_blog_routes_redirect_to_indexable_urls(self):
        blog_list = self.client.get("/blog/lista/?utm_source=legacy")
        blog_details = self.client.get("/blog/detalhes/?utm_source=legacy")

        self.assertEqual(blog_list.status_code, 301)
        self.assertEqual(blog_list["Location"], f"{reverse('institutional:blog')}?utm_source=legacy")
        self.assertEqual(blog_details.status_code, 301)
        self.assertEqual(
            blog_details["Location"],
            f"{reverse(
                'institutional:blog_detail',
                kwargs={'slug': 'selecao-controladores-ativos-alta-severidade'},
            )}?utm_source=legacy",
        )

    def test_blog_article_includes_article_social_metadata_and_post_image(self):
        response = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        post = BLOG_POSTS["selecao-controladores-ativos-alta-severidade"]
        expected_title = post.get("seo_title") or f"{post['title']} | Smart Control Brasil"
        expected_image = f"https://www.smartcontrolbrasil.com.br/static/{post['image']}"

        self.assertMetaProperty(response, "og:type", "article")
        self.assertMetaProperty(response, "og:title", expected_title)
        self.assertMetaProperty(response, "og:description", post["meta_description"])
        self.assertMetaProperty(
            response,
            "og:url",
            "https://www.smartcontrolbrasil.com.br/blog/selecao-controladores-ativos-alta-severidade/",
        )
        self.assertMetaProperty(response, "og:image", expected_image)
        self.assertMetaName(response, "twitter:title", expected_title)
        self.assertMetaName(response, "twitter:description", post["meta_description"])
        self.assertMetaName(response, "twitter:image", expected_image)

    def test_sitemap_returns_public_https_urls_without_noindex_pages(self):
        urls = self.sitemap_urls()

        self.assertIn("https://www.smartcontrolbrasil.com.br/", urls)
        strategic_solution_urls = (
            "https://www.smartcontrolbrasil.com.br/xyron/",
            "https://www.smartcontrolbrasil.com.br/mitsubishi-automacao-industrial/",
            "https://www.smartcontrolbrasil.com.br/manutencao-industrial-campo/",
            "https://www.smartcontrolbrasil.com.br/sistemas-websites-python/",
        )
        for strategic_url in strategic_solution_urls:
            with self.subTest(strategic_url=strategic_url):
                self.assertIn(strategic_url, urls)
                self.assertEqual(urls.count(strategic_url), 1)
        self.assertIn("https://www.smartcontrolbrasil.com.br/blog/", urls)
        self.assertIn("https://www.smartcontrolbrasil.com.br/autor/marcelo-custodio/", urls)
        self.assertIn("https://www.smartcontrolbrasil.com.br/contato/", urls)
        self.assertIn(
            "https://www.smartcontrolbrasil.com.br/blog/selecao-controladores-ativos-alta-severidade/",
            urls,
        )
        self.assertEqual(len(urls), len(set(urls)))
        self.assertFalse(any("/admin/" in url for url in urls))
        self.assertFalse(any("/login/" in url for url in urls))
        self.assertFalse(any("/cadastro/" in url for url in urls))
        self.assertFalse(any("/modelos/" in url for url in urls))
        self.assertFalse(any("localhost" in url or "127.0.0.1" in url for url in urls))
        self.assertIn("https://www.smartcontrolbrasil.com.br/loja/", urls)
        legacy_urls = (
            "https://www.smartcontrolbrasil.com.br/sobre/",
            "https://www.smartcontrolbrasil.com.br/parceiros/mitsubishi-automacao/",
            "https://www.smartcontrolbrasil.com.br/parceiros/automacao-industrial-clps/",
            "https://www.smartcontrolbrasil.com.br/parceiros/xyron-robotics/",
            "https://www.smartcontrolbrasil.com.br/parceiros/agraz/",
            "https://www.smartcontrolbrasil.com.br/projetos/",
            "https://www.smartcontrolbrasil.com.br/projetos/detalhes/",
            "https://www.smartcontrolbrasil.com.br/blog/automacao-industrial-conectada-gestao/",
            "https://www.smartcontrolbrasil.com.br/blog/dashboards-decisoes-melhores/",
            "https://www.smartcontrolbrasil.com.br/blog/iot-mudando-negocios/",
            "https://www.smartcontrolbrasil.com.br/blog/manutencao-tpm-confiabilidade-sistemas-automatizados/",
            "https://www.smartcontrolbrasil.com.br/blog/paineis-eletricos-automacao/",
            "https://www.smartcontrolbrasil.com.br/blog/aplicacoes-reais-robos-brasil/",
            "https://www.smartcontrolbrasil.com.br/blog/robotica-escolas-empresas-cidades/",
            "https://www.smartcontrolbrasil.com.br/blog/integrar-sensores-maquinas-sistemas/",
            "https://www.smartcontrolbrasil.com.br/blog/automacao-conectada-maquinas-sensores-sistemas/",
            "https://www.smartcontrolbrasil.com.br/blog/dados-operacionais-empresa-inteligente/",
            "https://www.smartcontrolbrasil.com.br/blog/pagina/2/",
            "https://www.smartcontrolbrasil.com.br/faq/",
        )
        for legacy_url in legacy_urls:
            with self.subTest(legacy_url=legacy_url):
                self.assertNotIn(legacy_url, urls)

        robot_urls = tuple(
            f"https://www.smartcontrolbrasil.com.br/xyron/{robot['slug']}/"
            for robot in XYRON_ROBOT_PAGES
        )
        for robot_url in robot_urls:
            with self.subTest(robot_url=robot_url):
                self.assertIn(robot_url, urls)
                self.assertEqual(urls.count(robot_url), 1)

        pillar_urls = tuple(
            f"https://www.smartcontrolbrasil.com.br{pillar['path']}"
            for pillar in XYRON_PILLAR_PAGES
        )
        for pillar_url in pillar_urls:
            with self.subTest(pillar_url=pillar_url):
                self.assertIn(pillar_url, urls)
                self.assertEqual(urls.count(pillar_url), 1)

        disabled_landing_urls = (
            "https://www.smartcontrolbrasil.com.br/engenharia-serralheria-industrial/",
            "https://www.smartcontrolbrasil.com.br/camara-climatica/",
            "https://www.smartcontrolbrasil.com.br/robo-seguranca-condominios/",
        )
        for disabled_url in disabled_landing_urls:
            with self.subTest(disabled_url=disabled_url):
                self.assertNotIn(disabled_url, urls)
        self.assertEqual(len(urls), 22 + len(BLOG_POSTS) + len(AUTHORS))

        for route_name in NOINDEX_ROUTE_NAMES:
            if route_name == "shop":
                continue
            try:
                path = reverse(f"institutional:{route_name}")
            except Exception:
                continue
            absolute_url = urljoin("https://www.smartcontrolbrasil.com.br", path)
            self.assertNotIn(absolute_url, urls)

    def test_sitemap_public_pages_do_not_render_internal_links_to_404_or_legacy_urls(self):
        sitemap_urls = self.sitemap_urls()
        allowed_hosts = {"smartcontrolbrasil.com.br", "www.smartcontrolbrasil.com.br", "testserver", ""}
        ignored_prefixes = ("/static/", "/media/", "/admin/", "/painel/", "/api/")
        legacy_paths = (
            "/sobre/",
            "/parceiros/mitsubishi-automacao/",
            "/parceiros/automacao-industrial-clps/",
            "/parceiros/xyron-robotics/",
            "/projetos/",
            "/projetos/detalhes/",
            "/parceiros/agraz/",
            "/blog/automacao-industrial-conectada-gestao/",
            "/blog/dashboards-decisoes-melhores/",
            "/blog/iot-mudando-negocios/",
            "/blog/manutencao-tpm-confiabilidade-sistemas-automatizados/",
            "/blog/paineis-eletricos-automacao/",
        )
        checked_links = set()
        broken_links = []
        legacy_links = []

        for sitemap_url in sitemap_urls:
            source_path = urlsplit(sitemap_url).path or "/"
            response = self.client.get(source_path, HTTP_HOST="smartcontrolbrasil.com.br", secure=True)
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()

            for legacy_path in legacy_paths:
                if f'href="{legacy_path}"' in html or f"href='{legacy_path}'" in html:
                    legacy_links.append((source_path, legacy_path))

            for href in re.findall(r'<a\b[^>]*\shref=["\']([^"\']+)["\']', html, flags=re.I):
                parsed = urlsplit(href)
                if parsed.scheme in {"mailto", "tel", "whatsapp"}:
                    continue
                if parsed.netloc not in allowed_hosts:
                    continue
                link_path = parsed.path
                if not link_path or link_path.startswith(ignored_prefixes):
                    continue

                request_path = link_path
                if parsed.query:
                    request_path = f"{request_path}?{parsed.query}"
                checked_links.add(request_path)

        for request_path in sorted(checked_links):
            response = self.client.get(request_path, HTTP_HOST="smartcontrolbrasil.com.br", secure=True)
            if response.status_code == 404:
                broken_links.append(request_path)

        self.assertEqual(legacy_links, [])
        self.assertEqual(broken_links, [])

    def test_sitemap_includes_public_commerce_urls_dynamically(self):
        robotica = Category.objects.create(name="Robótica", slug="robotica")
        climatizacao = Category.objects.create(name="Climatização", slug="climatizacao")
        refrigeracao = Category.objects.create(name="Refrigeração", slug="refrigeracao")
        automacao = Category.objects.create(name="Automação Industrial", slug="automacao-industrial")
        inactive_category = Category.objects.create(name="Categoria interna", slug="categoria-interna", active=False)
        Product.objects.create(name="LittleBot", slug="littlebot", category=robotica, active=True)
        Product.objects.create(name="Orbit", slug="orbit", category=robotica, active=True)
        camara_product = Product.objects.create(
            name="Câmara Climática sob medida",
            slug="camara-climatica-sob-medida",
            category=refrigeracao,
            active=True,
        )
        Product.objects.create(name="Produto futuro ativo", slug="produto-futuro-ativo", category=automacao, active=True)
        Product.objects.create(name="Produto inativo", slug="produto-inativo", category=robotica, active=False)
        Product.objects.create(name="Produto categoria inativa", slug="produto-categoria-inativa", category=inactive_category, active=True)

        urls = self.sitemap_urls()

        expected_urls = {
            "https://www.smartcontrolbrasil.com.br/loja/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/camara-climatica-sob-medida/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/produto-futuro-ativo/",
        }
        for expected_url in expected_urls:
            with self.subTest(expected_url=expected_url):
                self.assertIn(expected_url, urls)

        self.assertNotIn("https://www.smartcontrolbrasil.com.br/loja/produto/produto-inativo/", urls)
        self.assertNotIn("https://www.smartcontrolbrasil.com.br/loja/produto/produto-categoria-inativa/", urls)
        self.assertNotIn("https://www.smartcontrolbrasil.com.br/loja/categoria/categoria-interna/", urls)
        for noindex_url in (
            "https://www.smartcontrolbrasil.com.br/loja/categoria/robotica/",
            "https://www.smartcontrolbrasil.com.br/loja/categoria/climatizacao/",
            "https://www.smartcontrolbrasil.com.br/loja/categoria/refrigeracao/",
            "https://www.smartcontrolbrasil.com.br/loja/categoria/automacao-industrial/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/littlebot/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/orbit/",
        ):
            with self.subTest(noindex_url=noindex_url):
                self.assertNotIn(noindex_url, urls)

        self.assertIn("https://www.smartcontrolbrasil.com.br/xyron/littlebot/", urls)
        self.assertIn("https://www.smartcontrolbrasil.com.br/xyron/orbit/", urls)
        self.assertTrue(all(url.startswith("https://www.smartcontrolbrasil.com.br/") for url in urls))

        product_response = self.client.get(camara_product.get_absolute_url())
        self.assertEqual(product_response.status_code, 200)
        self.assertContains(product_response, camara_product.name)

        category_response = self.client.get(refrigeracao.get_absolute_url())
        self.assertEqual(category_response.status_code, 200)
        self.assertContains(category_response, camara_product.name)

    def test_robots_txt_points_to_production_sitemap_and_blocks_private_paths(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Sitemap: https://www.smartcontrolbrasil.com.br/sitemap.xml")
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /painel/")
        self.assertContains(response, "Disallow: /login/")
        self.assertContains(response, "Disallow: /cadastro/")



    def test_shop_metadata_is_unique_indexable_and_has_item_list_json_ld(self):
        Category.objects.create(name="Robótica", slug="robotica")
        Product.objects.create(name="LittleBot", slug="littlebot", category=Category.objects.get(slug="robotica"), active=True)
        Product.objects.create(name="Orbit", slug="orbit", category=Category.objects.get(slug="robotica"), active=True)

        response = self.client.get(reverse("commerce:shop"))
        html = response.content.decode()
        item_lists = self.graph_items(response, "ItemList")

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Loja de Automação, Robótica e Tecnologia | Smart Control Brasil")
        self.assertMetaDescription(response, "Conheça soluções em automação industrial, robótica Xyron, refrigeração e equipamentos tecnológicos com atendimento técnico especializado.")
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/loja/")
        self.assertNotContains(response, 'name="robots"')
        self.assertEqual(self.h1_texts(response), ["Loja"])
        self.assertMetaProperty(response, "og:url", "https://www.smartcontrolbrasil.com.br/loja/")
        self.assertMetaName(response, "twitter:title", "Loja de Automação, Robótica e Tecnologia | Smart Control Brasil")
        commerce_lists = [item for item in item_lists if item.get("name") == "Produtos públicos da loja Smart Control Brasil"]
        self.assertEqual(len(commerce_lists), 1)
        urls = [item["url"] for item in commerce_lists[0]["itemListElement"]]
        self.assertIn("https://www.smartcontrolbrasil.com.br/xyron/littlebot/", urls)
        self.assertIn("https://www.smartcontrolbrasil.com.br/xyron/orbit/", urls)
        self.assertNotIn("offers", json.dumps(commerce_lists[0]))
        self.assertNotIn("aggregateRating", html)

    def test_commerce_categories_are_accessible_noindex_follow_and_absent_from_sitemap(self):
        for name, slug in (
            ("Automação Industrial", "automacao-industrial"),
            ("Climatização", "climatizacao"),
            ("Refrigeração", "refrigeracao"),
            ("Robótica", "robotica"),
        ):
            Category.objects.create(name=name, slug=slug)

        urls = self.sitemap_urls()

        for slug in ("automacao-industrial", "climatizacao", "refrigeracao", "robotica"):
            with self.subTest(slug=slug):
                path = reverse("commerce:category", kwargs={"slug": slug})
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<meta name="robots" content="noindex,follow">')
                self.assertCanonical(response, f"https://www.smartcontrolbrasil.com.br{path}")
                self.assertNotIn(f"https://www.smartcontrolbrasil.com.br{path}", urls)

    def test_duplicate_store_products_redirect_to_xyron_canonical_pages(self):
        robotica = Category.objects.create(name="Robótica", slug="robotica")
        Product.objects.create(name="LittleBot", slug="littlebot", category=robotica, active=True)
        Product.objects.create(name="Orbit", slug="orbit", category=robotica, active=True)

        redirects = (
            (reverse("commerce:product_detail", kwargs={"slug": "littlebot"}), reverse("institutional:xyron_littlebot")),
            (reverse("commerce:product_detail", kwargs={"slug": "orbit"}), reverse("institutional:xyron_orbit")),
        )
        for source, target in redirects:
            with self.subTest(source=source):
                response = self.client.get(f"{source}?utm_source=loja")
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], f"{target}?utm_source=loja")
                self.assertEqual(self.client.get(target).status_code, 200)

        self.assertEqual(Product.objects.filter(slug__in=["littlebot", "orbit"]).count(), 2)
        self.assertEqual(Category.objects.filter(slug="robotica").count(), 1)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", "www.smartcontrolbrasil.com.br"])
    def test_missing_url_uses_institutional_404_template_with_real_404(self):
        response = self.client.get("/url-inexistente-etapa-15/")
        html = response.content.decode()

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "institutional/404.html")
        self.assertTitle(response, "Página não encontrada | Smart Control Brasil")
        self.assertContains(response, '<meta name="robots" content="noindex,follow">', status_code=404)
        for expected in ("Home", "Serviços", "Mitsubishi", "Xyron", "Blog", "Falar com a Smart Control"):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)
        self.assertNotIn("Traceback", html)
        self.assertNotIn("Django", html)

    def test_author_page_and_article_editorial_metadata(self):
        author_url = reverse("institutional:author_detail", kwargs={"slug": "marcelo-custodio"})
        author_response = self.client.get(author_url)
        author_html = author_response.content.decode()

        self.assertEqual(author_response.status_code, 200)
        self.assertTitle(author_response, MARCELO_CUSTODIO.seo_title)
        self.assertMetaDescription(author_response, MARCELO_CUSTODIO.seo_description)
        self.assertCanonical(author_response, "https://www.smartcontrolbrasil.com.br/autor/marcelo-custodio/")
        self.assertEqual(self.h1_texts(author_response), [MARCELO_CUSTODIO.name])
        self.assertNotContains(author_response, 'name="robots"')

        profile_pages = self.graph_items(author_response, "ProfilePage")
        people = self.graph_items(author_response, "Person")
        self.assertEqual(len(profile_pages), 1)
        self.assertEqual(len(people), 1)
        self.assertEqual(profile_pages[0]["mainEntity"], {"@id": self.AUTHOR_PERSON_ID})
        self.assertEqual(people[0]["name"], MARCELO_CUSTODIO.name)
        self.assertEqual(people[0]["jobTitle"], MARCELO_CUSTODIO.job_title)
        self.assertEqual(people[0]["description"], MARCELO_CUSTODIO.short_bio)
        self.assertEqual(people[0]["knowsAbout"], list(MARCELO_CUSTODIO.knows_about))
        self.assertEqual(people[0]["worksFor"], {"@id": "https://www.smartcontrolbrasil.com.br/#organization"})
        self.assertEqual(people[0]["url"], "https://www.smartcontrolbrasil.com.br/autor/marcelo-custodio/")
        self.assertEqual(
            people[0]["image"],
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/team/marcelo.png",
        )
        self.assertEqual(
            profile_pages[0]["primaryImageOfPage"],
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/team/marcelo.png",
        )
        self.assertNotIn("sameAs", people[0])
        self.assertIn(MARCELO_CUSTODIO.image_alt, author_html)
        self.assertIn('src="/static/institutional/imgs/team/marcelo.png"', author_html)
        self.assertIn(f'width="{MARCELO_CUSTODIO.image_width}"', author_html)
        self.assertIn(f'height="{MARCELO_CUSTODIO.image_height}"', author_html)

        for forbidden in (
            "CREA",
            "LinkedIn",
            "linkedin.com",
            "anos de experiência",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, people[0])
                self.assertNotIn(forbidden, author_html[author_html.find('<main>'):author_html.find('</main>')])

        for post in BLOG_POSTS_LIST:
            self.assertIn(post["title"], author_html)

        unchanged_slug = "selecao-controladores-ativos-alta-severidade"
        article_response = self.client.get(f"/blog/{unchanged_slug}/")
        article_html = article_response.content.decode()
        self.assertIn("Por ", article_html)
        self.assertIn(MARCELO_CUSTODIO.name, article_html)
        self.assertIn(author_url, article_html)
        self.assertIn('datetime="2026-08-01"', article_html)
        self.assertIn("Publicado em", article_html)
        self.assertIn("Atualizado em", article_html)
        self.assertIn("Sobre o autor", article_html)
        self.assertIn("Conheça o autor", article_html)
        self.assertIn(MARCELO_CUSTODIO.image_alt, article_html)
        self.assertIn('src="/static/institutional/imgs/team/marcelo.png"', article_html)

        people = self.graph_items(article_response, "Person")
        self.assertEqual(len(people), 1)
        self.assertEqual(
            people[0]["image"],
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/team/marcelo.png",
        )

        updated_slug = "convergencia-robotica-ia-firmwares-dedicados"
        updated_response = self.client.get(f"/blog/{updated_slug}/")
        updated_html = updated_response.content.decode()
        self.assertIn('datetime="2026-08-24"', updated_html)
        self.assertIn("Atualizado em", updated_html)

        blog_listing = self.client.get("/blog/")
        listing_html = blog_listing.content.decode()
        self.assertIn(MARCELO_CUSTODIO.name, listing_html)
        self.assertIn('datetime="2026-08-01"', listing_html)

        sitemap_urls = self.sitemap_urls()
        self.assertIn("https://www.smartcontrolbrasil.com.br/autor/marcelo-custodio/", sitemap_urls)

        for slug in BLOG_POSTS:
            blog_postings = self.graph_items(self.client.get(f"/blog/{slug}/"), "BlogPosting")
            self.assertEqual(len(blog_postings), 1)
            self.assertBlogPostingAuthorAndDates(blog_postings[0], slug)
            faq_pages = self.graph_items(self.client.get(f"/blog/{slug}/"), "FAQPage")
            breadcrumbs = self.graph_items(self.client.get(f"/blog/{slug}/"), "BreadcrumbList")
            if BLOG_POSTS[slug].get("faq"):
                self.assertEqual(len(faq_pages), 1)
            self.assertEqual(len(breadcrumbs), 1)

    def _script_sources(self, response):
        html = response.content.decode()
        return re.findall(r'<script[^>]+src="([^"]+)"', html)

    def _stylesheet_hrefs(self, response):
        html = response.content.decode()
        return re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)

    def test_xyron_pillar_pages_return_200_with_unique_seo_metadata(self):
        sitemap_urls = self.sitemap_urls()
        titles = set()
        descriptions = set()

        for pillar in XYRON_PILLAR_PAGES:
            canonical = f"https://www.smartcontrolbrasil.com.br{pillar['path']}"
            with self.subTest(path=pillar["path"]):
                response = self.client.get(f"{pillar['path']}?utm_source=google")
                html = response.content.decode()
                body = html.split("<body", 1)[1]

                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.h1_texts(response), [pillar["h1"]])
                self.assertTitle(response, pillar["title"])
                self.assertMetaDescription(response, pillar["description"])
                self.assertNotIn(pillar["description"], body)
                self.assertCanonical(response, canonical)
                self.assertNotContains(response, 'name="robots"')
                self.assertMetaProperty(response, "og:title", pillar["title"])
                self.assertMetaProperty(response, "og:description", pillar["description"])
                self.assertMetaProperty(response, "og:url", canonical)
                self.assertMetaProperty(response, "og:type", "website")
                self.assertMetaName(response, "twitter:title", pillar["title"])
                self.assertMetaName(response, "twitter:description", pillar["description"])
                self.assertIn(canonical, sitemap_urls)
                self.assertEqual(html.count('fetchpriority="high"'), 1)
                self.assertNotIn("swiper-bundle.min.js", html)
                self.assertNotIn("wow.min.js", html)

                titles.add(pillar["title"])
                descriptions.add(pillar["description"])

        self.assertEqual(len(titles), len(XYRON_PILLAR_PAGES))
        self.assertEqual(len(descriptions), len(XYRON_PILLAR_PAGES))

    def test_xyron_pillar_pages_include_webpage_service_faq_and_itemlist(self):
        for pillar in XYRON_PILLAR_PAGES:
            with self.subTest(path=pillar["path"]):
                response = self.client.get(pillar["path"])
                html = response.content.decode()

                web_pages = self.graph_items(response, "WebPage")
                services = self.graph_items(response, "Service")
                faq_pages = self.graph_items(response, "FAQPage")
                item_lists = self.graph_items(response, "ItemList")
                products = self.graph_items(response, "Product")
                breadcrumbs = self.graph_items(response, "BreadcrumbList")

                self.assertEqual(len(web_pages), 1)
                self.assertEqual(len(services), 1)
                self.assertEqual(len(faq_pages), 1)
                self.assertEqual(len(item_lists), 1)
                self.assertEqual(products, [])
                self.assertEqual(len(breadcrumbs), 1)
                self.assertEqual(
                    [item["name"] for item in breadcrumbs[0]["itemListElement"]],
                    ["Início", pillar["breadcrumb_label"]],
                )

                faq_entities = faq_pages[0]["mainEntity"]
                self.assertEqual(len(faq_entities), len(pillar["faqs"]))
                for (question, answer), entity in zip(pillar["faqs"], faq_entities):
                    self.assertEqual(entity["name"], question)
                    self.assertEqual(entity["acceptedAnswer"]["text"], answer)
                    self.assertIn(question, html)
                    self.assertIn(answer, html)

                list_items = item_lists[0]["itemListElement"]
                self.assertEqual(len(list_items), len(pillar["related_robots"]))

    def test_xyron_pillar_pages_link_to_products_xyron_and_back(self):
        pillar_links = {
            "robotica_educacional": reverse("institutional:robotica_educacional"),
            "robos_limpeza_profissional": reverse("institutional:robos_limpeza_profissional"),
            "robos_seguranca_patrimonial": reverse("institutional:robos_seguranca_patrimonial"),
        }
        product_links = {
            "littlebot": reverse("institutional:xyron_littlebot"),
            "hygibot_dune_bot": reverse("institutional:xyron_hygibot_dune_bot"),
            "orbit": reverse("institutional:xyron_orbit"),
            "buddy_bot": reverse("institutional:xyron_buddy_bot"),
        }

        for pillar in XYRON_PILLAR_PAGES:
            response = self.client.get(pillar["path"])
            html = response.content.decode()
            self.assertIn(reverse("institutional:xyron"), html)
            for robot_key in pillar["related_robots"]:
                self.assertIn(product_links[robot_key], html)

        littlebot = self.client.get("/xyron/littlebot/").content.decode()
        self.assertIn(pillar_links["robotica_educacional"], littlebot)

        hygibot = self.client.get("/xyron/hygibot-dune-bot/").content.decode()
        self.assertIn(pillar_links["robos_limpeza_profissional"], hygibot)

        orbit = self.client.get("/xyron/orbit/").content.decode()
        buddy = self.client.get("/xyron/buddy-bot/").content.decode()
        self.assertIn(pillar_links["robos_seguranca_patrimonial"], orbit)
        self.assertIn(pillar_links["robos_seguranca_patrimonial"], buddy)

        xyron = self.client.get("/xyron/").content.decode()
        for link in pillar_links.values():
            self.assertIn(link, xyron)

    def test_xyron_pillar_pages_do_not_canibalize_product_titles(self):
        product_titles = {robot["title"] for robot in XYRON_ROBOT_PAGES}
        hub_title = "Robôs Inteligentes Xyron Robotics | Smart Control Brasil"

        for pillar in XYRON_PILLAR_PAGES:
            self.assertNotIn(pillar["title"], product_titles)
            self.assertNotEqual(pillar["title"], hub_title)
            self.assertNotEqual(
                pillar["h1"],
                "Xyron Robotics — Robótica Inteligente para Segurança, Educação e Empresas",
            )

    def test_xyron_pillar_pages_use_base_assets_without_optional_plugins(self):
        response = self.client.get("/robotica-educacional/")
        scripts = self._script_sources(response)
        stylesheets = self._stylesheet_hrefs(response)

        self.assertEqual(len(scripts), 13)
        self.assertEqual(len(stylesheets), 6)
        self.assertTrue(any("preloader-critical.js" in source for source in scripts))
        self.assertFalse(any("swiper" in source for source in scripts))
        self.assertFalse(any("wow.min.js" in source for source in scripts))
        self.assertTrue(any("main.js" in source for source in scripts))

    def test_stage19_diff_does_not_add_forbidden_climate_terms(self):
        result = subprocess.run(
            [
                "git",
                "diff",
                "HEAD",
                "--",
                "src/institutional/presentation/",
                "templates/",
                "static/",
                "config/",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        )
        added_lines = [
            line[1:].lower()
            for line in result.stdout.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        added_text = "\n".join(added_lines)
        for term in FORBIDDEN_CLIMATE_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term.lower(), added_text)


LEGACY_SEO_REDIRECTS = (
    (
        "/blog/aplicacoes-reais-robos-brasil/",
        reverse(
            "institutional:blog_detail",
            kwargs={"slug": "inovacao-que-aparece-e-gera-valor"},
        ),
    ),
    (
        "/blog/robotica-escolas-empresas-cidades/",
        reverse(
            "institutional:blog_detail",
            kwargs={"slug": "inovacao-que-aparece-e-gera-valor"},
        ),
    ),
    (
        "/blog/integrar-sensores-maquinas-sistemas/",
        reverse(
            "institutional:blog_detail",
            kwargs={"slug": "informacao-precisa-para-agir-melhor"},
        ),
    ),
    (
        "/blog/automacao-conectada-maquinas-sensores-sistemas/",
        reverse(
            "institutional:blog_detail",
            kwargs={"slug": "informacao-precisa-para-agir-melhor"},
        ),
    ),
    (
        "/blog/dados-operacionais-empresa-inteligente/",
        reverse(
            "institutional:blog_detail",
            kwargs={"slug": "historico-indicadores-decisoes-consistentes"},
        ),
    ),
    ("/blog/pagina/2/", reverse("institutional:blog")),
    ("/faq/", reverse("institutional:home")),
)

LEGACY_SEO_SOURCE_URLS = tuple(source for source, _ in LEGACY_SEO_REDIRECTS)

FORBIDDEN_CLIMATE_TERMS = (
    "câmara climática",
    "câmaras climáticas",
    "camara climatica",
    "camaras climaticas",
)


class LegacySeoRedirectTests(TestCase):
    def test_legacy_seo_urls_return_301_with_preserved_query_string(self):
        for source, target in LEGACY_SEO_REDIRECTS:
            with self.subTest(source=source):
                response = self.client.get(f"{source}?utm_source=legacy&ref=old")
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], f"{target}?utm_source=legacy&ref=old")

    def test_legacy_seo_redirect_destinations_return_200_without_loops(self):
        for source, target in LEGACY_SEO_REDIRECTS:
            with self.subTest(source=source):
                self.assertNotEqual(source, target)
                response = self.client.get(source)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response["Location"], target)
                destination_response = self.client.get(target)
                self.assertEqual(destination_response.status_code, 200)

    def test_unknown_url_still_returns_real_404_with_noindex(self):
        response = self.client.get("/pagina-legada-inexistente-teste/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, '<meta name="robots" content="noindex,follow">', status_code=404)

    def test_legacy_seo_urls_are_absent_from_sitemap(self):
        response = self.client.get("/sitemap.xml")
        xml = response.content.decode()
        for legacy_url in LEGACY_SEO_SOURCE_URLS:
            with self.subTest(legacy_url=legacy_url):
                self.assertNotIn(f"https://www.smartcontrolbrasil.com.br{legacy_url}", xml)


class AuthorPortraitTests(TestCase):
    AUTHOR_IMAGE_STATIC = static("institutional/imgs/team/marcelo.png")
    AUTHOR_IMAGE_ABSOLUTE = (
        "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/team/marcelo.png"
    )

    def structured_data(self, response):
        html = response.content.decode()
        start_marker = '<script type="application/ld+json">'
        end_marker = "</script>"
        blocks = []
        start = html.find(start_marker)
        while start != -1:
            start += len(start_marker)
            end = html.find(end_marker, start)
            blocks.append(json.loads(html[start:end]))
            start = html.find(start_marker, end + len(end_marker))
        return blocks

    def graph_items(self, response, item_type=None):
        items = []
        for payload in self.structured_data(response):
            graph = payload.get("@graph", [])
            items.extend(graph if isinstance(graph, list) else [graph])
        if item_type:
            return [item for item in items if item.get("@type") == item_type]
        return items

    def assertPortraitMarkup(self, response, lazy_expected):
        html = response.content.decode()
        self.assertIn(self.AUTHOR_IMAGE_STATIC, html)
        self.assertIn(MARCELO_CUSTODIO.image_alt, html)
        self.assertIn(f'width="{MARCELO_CUSTODIO.image_width}"', html)
        self.assertIn(f'height="{MARCELO_CUSTODIO.image_height}"', html)
        portrait_match = re.search(
            r'<figure class="author-portrait[^"]*">.*?<img[^>]+>',
            html,
            flags=re.S,
        )
        self.assertIsNotNone(portrait_match)
        if lazy_expected:
            self.assertIn('loading="lazy"', portrait_match.group(0))
        else:
            self.assertNotIn('loading="lazy"', portrait_match.group(0))

    def test_author_page_displays_portrait_without_lazy_loading(self):
        response = self.client.get(
            reverse("institutional:author_detail", kwargs={"slug": MARCELO_CUSTODIO.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertPortraitMarkup(response, lazy_expected=False)

    def test_article_author_blocks_display_portrait_for_all_posts(self):
        for slug in BLOG_POSTS:
            with self.subTest(slug=slug):
                response = self.client.get(f"/blog/{slug}/")
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertIn("Sobre o autor", html)
                self.assertIn(self.AUTHOR_IMAGE_STATIC, html)
                self.assertIn(MARCELO_CUSTODIO.image_alt, html)

    def test_about_page_displays_technical_author_portrait(self):
        response = self.client.get("/empresa/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Responsabilidade Técnica e Editorial", html)
        self.assertIn(self.AUTHOR_IMAGE_STATIC, html)
        self.assertIn(MARCELO_CUSTODIO.image_alt, html)

    def test_person_and_profile_page_schemas_include_author_image(self):
        author_response = self.client.get(
            reverse("institutional:author_detail", kwargs={"slug": MARCELO_CUSTODIO.slug})
        )
        people = self.graph_items(author_response, "Person")
        profile_pages = self.graph_items(author_response, "ProfilePage")
        self.assertEqual(people[0]["image"], self.AUTHOR_IMAGE_ABSOLUTE)
        self.assertEqual(profile_pages[0]["primaryImageOfPage"], self.AUTHOR_IMAGE_ABSOLUTE)

    def test_blogposting_keeps_author_id_and_person_image_on_articles(self):
        slug = "selecao-controladores-ativos-alta-severidade"
        response = self.client.get(f"/blog/{slug}/")
        blog_postings = self.graph_items(response, "BlogPosting")
        people = self.graph_items(response, "Person")
        self.assertEqual(blog_postings[0]["author"], {"@id": MARCELO_CUSTODIO.json_ld_id})
        self.assertEqual(people[0]["image"], self.AUTHOR_IMAGE_ABSOLUTE)
        editorial = BLOG_POST_EDITORIAL[slug]
        self.assertEqual(blog_postings[0]["datePublished"], editorial["date_published"])
        self.assertEqual(blog_postings[0]["dateModified"], editorial["date_modified"])

    def test_commit_diff_does_not_add_forbidden_climate_terms(self):
        result = subprocess.run(
            [
                "git",
                "diff",
                "HEAD",
                "--",
                "src/institutional/presentation/",
                "templates/",
                "static/",
                "config/",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        )
        added_lines = [
            line[1:].lower()
            for line in result.stdout.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        added_text = "\n".join(added_lines)
        for term in FORBIDDEN_CLIMATE_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term.lower(), added_text)


@override_settings(ALLOWED_HOSTS=["testserver", "smartcontrolbrasil.com.br"])
class PreloaderHotfixTests(TestCase):
    MAIN_JS_PATH = Path(__file__).resolve().parents[4] / "static/institutional/js/main.js"
    CRITICAL_JS_PATH = (
        Path(__file__).resolve().parents[4] / "static/institutional/js/preloader-critical.js"
    )
    CACHE_BUST = INSTITUTIONAL_MAIN_JS_CACHE_BUST
    INSTITUTIONAL_ROUTES = (
        "home",
        "about",
        "services",
        "blog",
        "contact",
        "xyron",
        "xyron_littlebot",
        "manutencao_industrial_campo",
        "sistemas_websites_python",
        "robotica_educacional",
    )

    def home_html(self):
        return self.client.get(reverse("institutional:home")).content.decode()

    def test_preloader_uses_semantic_close_button(self):
        html = self.home_html()
        self.assertIn('class="preloader-close"', html)
        self.assertIn('type="button"', html)
        self.assertIn('aria-label="Fechar tela de carregamento"', html)
        self.assertIn("<noscript><style>#preloader{display:none!important}</style></noscript>", html)

    def test_critical_preloader_controller_loads_before_main_js(self):
        html = self.home_html()
        critical_index = html.find("preloader-critical.js")
        main_index = html.find("main.js?v=" + self.CACHE_BUST)
        self.assertNotEqual(critical_index, -1)
        self.assertNotEqual(main_index, -1)
        self.assertLess(critical_index, main_index)
        self.assertNotIn("defer", html[critical_index : critical_index + 120])

    def test_main_js_has_cache_busting_query_string(self):
        html = self.home_html()
        self.assertIn(f"main.js?v={self.CACHE_BUST}", html)

    def test_main_js_no_longer_references_masonry(self):
        main_js = self.MAIN_JS_PATH.read_text(encoding="utf-8")
        self.assertNotIn("resourcesHubMasonry", main_js)
        self.assertNotIn(".masonry(", main_js)

    def test_critical_preloader_script_is_self_contained(self):
        critical_js = self.CRITICAL_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("smart360ClosePreloader", critical_js)
        self.assertIn("Escape", critical_js)
        self.assertIn("DOMContentLoaded", critical_js)
        self.assertIn("4000", critical_js)
        self.assertNotIn("jquery", critical_js.lower())
        self.assertNotIn('"load"', critical_js)
        self.assertNotIn("'load'", critical_js)

    PILLAR_ROUTES = (
        "robotica_educacional",
        "robos_seguranca_patrimonial",
        "robos_limpeza_profissional",
    )

    def test_stage19_pillar_pages_remain_indexable_and_in_sitemap(self):
        sitemap = self.client.get(
            "/sitemap.xml",
            HTTP_HOST="smartcontrolbrasil.com.br",
            secure=True,
        ).content.decode()
        for route in self.PILLAR_ROUTES:
            with self.subTest(route=route):
                response = self.client.get(reverse(f"institutional:{route}"))
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertNotIn('content="noindex', html.lower())
                self.assertIn(reverse(f"institutional:{route}").strip("/"), sitemap)

    def test_institutional_routes_still_return_200(self):
        for route in self.INSTITUTIONAL_ROUTES:
            with self.subTest(route=route):
                response = self.client.get(reverse(f"institutional:{route}"))
                self.assertEqual(response.status_code, 200)

    def test_legacy_redirects_sitemap_and_404_remain_correct(self):
        redirect_response = self.client.get("/parceiros/xyron-robotics/")
        self.assertEqual(redirect_response.status_code, 301)

        sitemap_response = self.client.get(
            "/sitemap.xml",
            HTTP_HOST="smartcontrolbrasil.com.br",
            secure=True,
        )
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertIn("robotica-educacional", sitemap_response.content.decode())

        missing_response = self.client.get("/pagina-inexistente-hotfix/")
        self.assertEqual(missing_response.status_code, 404)
        self.assertContains(
            missing_response,
            '<meta name="robots" content="noindex,follow">',
            status_code=404,
        )

        home_html = self.home_html()
        self.assertIn('"@type":"Organization"', home_html.replace(" ", ""))


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional dependency
    sync_playwright = None


@override_settings(ALLOWED_HOSTS=["*"])
class PreloaderHotfixPlaywrightTests(StaticLiveServerTestCase):
    HOLD_AUTO_CLOSE = """
        (function () {
            var nativeAddEventListener = window.addEventListener;
            var nativeDocumentAddEventListener = document.addEventListener;
            window.addEventListener = function (type, listener, options) {
                if (type === "load") {
                    return;
                }
                return nativeAddEventListener.call(this, type, listener, options);
            };
            document.addEventListener = function (type, listener, options) {
                if (type === "DOMContentLoaded") {
                    return;
                }
                return nativeDocumentAddEventListener.call(this, type, listener, options);
            };
            var nativeSetTimeout = window.setTimeout;
            window.setTimeout = function (callback, delay) {
                if (delay === 4000) {
                    return 0;
                }
                return nativeSetTimeout(callback, delay);
            };
        })();
    """

    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            raise unittest.SkipTest("Playwright não instalado neste ambiente.")
        super().setUpClass()

    def test_preloader_closes_on_load_click_escape_and_failsafe(self):
        with sync_playwright() as playwright_context:
            browser = playwright_context.chromium.launch(headless=True)

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(self.live_server_url + "/", wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            self.assertEqual(page.locator("#preloader").count(), 0)
            self.assertFalse(any("masonry is not a function" in item.lower() for item in errors))
            clickable = page.evaluate(
                """() => {
                    const link = document.querySelector('header nav a[href="/empresa/"]');
                    if (!link) {
                        return false;
                    }
                    const rect = link.getBoundingClientRect();
                    const target = document.elementFromPoint(
                        rect.left + rect.width / 2,
                        rect.top + rect.height / 2
                    );
                    return target === link || link.contains(target);
                }"""
            )
            self.assertTrue(clickable)

            click_page = browser.new_page(viewport={"width": 1440, "height": 900})
            click_page.add_init_script(self.HOLD_AUTO_CLOSE)
            click_page.goto(self.live_server_url + "/", wait_until="domcontentloaded")
            self.assertEqual(click_page.locator("#preloader").count(), 1)
            click_page.locator(".preloader-close").click()
            click_page.wait_for_timeout(400)
            self.assertEqual(click_page.locator("#preloader").count(), 0)

            escape_page = browser.new_page(viewport={"width": 390, "height": 844})
            escape_page.add_init_script(self.HOLD_AUTO_CLOSE)
            escape_page.goto(self.live_server_url + "/", wait_until="domcontentloaded")
            escape_page.keyboard.press("Escape")
            escape_page.wait_for_timeout(400)
            self.assertEqual(escape_page.locator("#preloader").count(), 0)

            blocked = browser.new_page(viewport={"width": 1440, "height": 900})
            blocked.route("**/main.js*", lambda route: route.abort())
            blocked.goto(self.live_server_url + "/", wait_until="domcontentloaded")
            blocked.wait_for_timeout(4500)
            self.assertEqual(blocked.locator("#preloader").count(), 0)

            browser.close()

    def test_core_interactions_still_work_after_preloader_hotfix(self):
        with sync_playwright() as playwright_context:
            browser = playwright_context.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto(self.live_server_url + "/servicos/", wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            page.locator(".sidebar__toggle, .bar-icon").first.click(force=True)
            page.wait_for_timeout(500)
            self.assertGreater(page.locator(".offcanvas__area, .offcanvas__overlay").count(), 0)

            page.goto(self.live_server_url + "/servicos/", wait_until="load")
            page.locator(".faq__area").scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            self.assertTrue(
                page.evaluate("() => Boolean(window.bootstrap && window.bootstrap.Collapse)")
            )
            collapsed_panel = page.locator(".faq__item .accordion-collapse:not(.show)").first
            self.assertGreater(collapsed_panel.count(), 0)
            panel_id = collapsed_panel.get_attribute("id")
            page.evaluate(
                """(panelId) => {
                    const panel = document.getElementById(panelId);
                    if (!panel || !window.bootstrap) {
                        return;
                    }
                    bootstrap.Collapse.getOrCreateInstance(panel).show();
                }""",
                panel_id,
            )
            page.wait_for_function(
                f"() => document.getElementById('{panel_id}')?.classList.contains('show')",
                timeout=5000,
            )

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(500)
            self.assertEqual(page.locator("#scroll-percentage").count(), 1)
            self.assertIn("livia.smartcontrolbrasil.com.br/widget.js", page.content())

            manutencao = browser.new_page(viewport={"width": 1440, "height": 900})
            manutencao.goto(
                self.live_server_url + "/manutencao-industrial-campo/",
                wait_until="load",
            )
            self.assertTrue(
                any(
                    "odometer" in source
                    for source in manutencao.locator("script[src]").evaluate_all(
                        "elements => elements.map(el => el.getAttribute('src') || '')"
                    )
                )
            )

            sistemas = browser.new_page(viewport={"width": 1440, "height": 900})
            sistemas.goto(
                self.live_server_url + "/sistemas-websites-python/",
                wait_until="load",
            )
            self.assertIn("vanilla-tilt.js", sistemas.content())

            browser.close()


class FrontendPerformanceTests(TestCase):
    CORE_SCRIPT_MARKERS = (
        "institutional/js/vendor/jquery-3.7.1.min.js",
        "institutional/js/vendor/bootstrap.bundle.min.js",
        "institutional/js/main.js",
        "institutional/js/plugins/gsap.js",
    )
    REMOVED_GLOBAL_SCRIPT_MARKERS = (
        "institutional/js/vendor/magnific-popup.min.js",
        "institutional/js/vendor/type.js",
        "institutional/js/plugins/nice-select.min.js",
        "institutional/js/plugins/parallax-scroll.js",
        "institutional/js/plugins/jquery.countdown.min.js",
        "institutional/js/plugins/isotope-docs.min.js",
        "institutional/js/vendor/ajax-form.js",
    )

    def script_sources(self, response):
        html = response.content.decode()
        return re.findall(r'<script[^>]+src="([^"]+)"', html)

    def stylesheet_hrefs(self, response):
        html = response.content.decode()
        return re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html)

    def content_images(self, response):
        html = response.content.decode()
        tags = re.findall(r"<img\b[^>]*>", html, flags=re.I)
        content_images = []
        for tag in tags:
            alt_match = re.search(r'alt="([^"]*)"', tag)
            alt = alt_match.group(1) if alt_match else None
            if alt == "":
                continue
            content_images.append(tag)
        return content_images

    def test_core_assets_remain_on_contact_page(self):
        response = self.client.get(reverse("institutional:contact"))
        sources = self.script_sources(response)
        for marker in self.CORE_SCRIPT_MARKERS:
            with self.subTest(marker=marker):
                self.assertTrue(any(marker in source for source in sources))

    def test_removed_plugins_are_not_loaded_globally(self):
        response = self.client.get(reverse("institutional:contact"))
        sources = self.script_sources(response)
        for marker in self.REMOVED_GLOBAL_SCRIPT_MARKERS:
            with self.subTest(marker=marker):
                self.assertFalse(any(marker in source for source in sources))

    def test_swiper_and_wow_load_only_on_interactive_pages(self):
        home_sources = self.script_sources(self.client.get(reverse("institutional:home")))
        contact_sources = self.script_sources(self.client.get(reverse("institutional:contact")))

        self.assertTrue(any("swiper.min.js" in source for source in home_sources))
        self.assertTrue(any("wow.js" in source for source in home_sources))
        self.assertFalse(any("swiper.min.js" in source for source in contact_sources))
        self.assertFalse(any("wow.js" in source for source in contact_sources))

    def test_odometer_assets_load_only_on_manutencao_page(self):
        manutencao_css = self.stylesheet_hrefs(
            self.client.get(reverse("institutional:manutencao_industrial_campo"))
        )
        contact_css = self.stylesheet_hrefs(self.client.get(reverse("institutional:contact")))
        self.assertTrue(any("odometer.min.css" in href for href in manutencao_css))
        self.assertFalse(any("odometer.min.css" in href for href in contact_css))

    def test_vanilla_tilt_loads_only_on_sistemas_python_page(self):
        sistemas_sources = self.script_sources(
            self.client.get(reverse("institutional:sistemas_websites_python"))
        )
        contact_sources = self.script_sources(self.client.get(reverse("institutional:contact")))
        self.assertTrue(any("vanilla-tilt.js" in source for source in sistemas_sources))
        self.assertFalse(any("vanilla-tilt.js" in source for source in contact_sources))

    def test_google_analytics_and_livia_widget_remain_configured(self):
        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode()
        self.assertIn('src="https://www.googletagmanager.com/gtag/js?id=G-9XGJDZ0N87"', html)
        self.assertIn('async src="https://www.googletagmanager.com/gtag/js?id=G-9XGJDZ0N87"', html)
        self.assertIn("https://livia.smartcontrolbrasil.com.br/widget.js", html)
        self.assertIn('data-tenant="smart-control-brasil"', html)

    def test_main_js_keeps_defer_and_vendor_order_before_main(self):
        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode()
        jquery_index = html.find("institutional/js/vendor/jquery-3.7.1.min.js")
        gsap_index = html.find("institutional/js/plugins/gsap.js")
        main_index = html.find(f"institutional/js/main.js?v={INSTITUTIONAL_MAIN_JS_CACHE_BUST}")
        self.assertIn(
            f'defer src="/static/institutional/js/main.js?v={INSTITUTIONAL_MAIN_JS_CACHE_BUST}"',
            html,
        )
        self.assertNotEqual(jquery_index, -1)
        self.assertNotEqual(gsap_index, -1)
        self.assertNotEqual(main_index, -1)
        self.assertLess(jquery_index, main_index)
        self.assertLess(gsap_index, main_index)

    def test_home_keeps_single_high_priority_image(self):
        response = self.client.get(reverse("institutional:home"))
        html = response.content.decode()
        high_priority_images = re.findall(
            r'<img\b[^>]*fetchpriority="high"[^>]*>',
            html,
            flags=re.I,
        )
        self.assertEqual(len(high_priority_images), 1)
        self.assertIn('loading="eager"', high_priority_images[0])

    def test_content_images_include_intrinsic_dimensions_on_key_pages(self):
        pages = (
            reverse("institutional:home"),
            reverse("institutional:about"),
            reverse("institutional:blog"),
            reverse(
                "institutional:blog_detail",
                kwargs={"slug": "selecao-controladores-ativos-alta-severidade"},
            ),
        )
        for path in pages:
            with self.subTest(path=path):
                response = self.client.get(path)
                for tag in self.content_images(response):
                    self.assertRegex(tag, r'\bwidth=(?:\"|\&quot;)\d+(?:\"|\&quot;)', msg=tag)
                    self.assertRegex(tag, r'\bheight=(?:\"|\&quot;)\d+(?:\"|\&quot;)', msg=tag)

    def test_author_portrait_keeps_300_by_340_dimensions(self):
        response = self.client.get(
            reverse("institutional:author_detail", kwargs={"slug": MARCELO_CUSTODIO.slug})
        )
        html = response.content.decode()
        self.assertIn('width="300"', html)
        self.assertIn('height="340"', html)
        self.assertIn("institutional/imgs/team/marcelo.png", html)

    def test_marcelo_png_is_tracked_as_regular_file(self):
        result = subprocess.run(
            ["git", "ls-files", "-s", "static/institutional/imgs/team/marcelo.png"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        )
        self.assertTrue(result.stdout.startswith("100644 "))

    def test_legacy_redirects_and_real_404_remain_after_frontend_changes(self):
        legacy_response = self.client.get("/faq/")
        self.assertEqual(legacy_response.status_code, 301)
        missing_response = self.client.get("/pagina-legada-inexistente-teste/")
        self.assertEqual(missing_response.status_code, 404)
        self.assertContains(
            missing_response,
            '<meta name="robots" content="noindex,follow">',
            status_code=404,
        )

    def test_structured_data_remains_present_on_author_page(self):
        response = self.client.get(
            reverse("institutional:author_detail", kwargs={"slug": MARCELO_CUSTODIO.slug})
        )
        self.assertContains(response, '"@type":"Person"')
        self.assertContains(response, '"@type":"ProfilePage"')
        self.assertContains(
            response,
            "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/team/marcelo.png",
        )

    def test_stage18_diff_does_not_add_forbidden_climate_terms(self):
        result = subprocess.run(
            [
                "git",
                "diff",
                "114e1cbee4dd4aeb55a56482a1c6855b8d1c7185",
                "--",
                "src/institutional/presentation/",
                "templates/",
                "static/",
                "config/",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        )
        added_lines = [
            line[1:].lower()
            for line in result.stdout.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        added_text = "\n".join(added_lines)
        for term in FORBIDDEN_CLIMATE_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term.lower(), added_text)


class AuthenticationRoutesTests(TestCase):
    def test_login_page_remains_available(self):
        response = self.client.get(reverse("institutional:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acesso restrito")

    def test_signup_authenticates_and_redirects_to_home_by_default(self):
        response = self.client.post(
            reverse("institutional:signup"),
            {
                "username": "signup-player",
                "password1": "SenhaTeste123!Segura",
                "password2": "SenhaTeste123!Segura",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("institutional:home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_signup_respects_safe_next_parameter(self):
        next_url = reverse("institutional:contact")
        response = self.client.post(
            reverse("institutional:signup"),
            {
                "username": "signup-next-player",
                "password1": "SenhaTeste123!Segura",
                "password2": "SenhaTeste123!Segura",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, next_url)

    def test_login_rejects_external_next_and_redirects_to_home(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="login-safe-next",
            password="SenhaTeste123!Segura",
        )

        response = self.client.post(
            reverse("institutional:login"),
            {
                "username": "login-safe-next",
                "password": "SenhaTeste123!Segura",
                "next": "https://site-malicioso.example/",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("institutional:home"))

    def test_logout_post_ends_user_session(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="logout-player",
            password="SenhaTeste123!Segura",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("institutional:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("institutional:home"))
        self.assertFalse("_auth_user_id" in self.client.session)
