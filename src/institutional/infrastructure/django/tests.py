import json
import re
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import urljoin
from xml.etree import ElementTree

from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse

from src.commerce.models import Category
from src.commerce.models import Product
from src.institutional.presentation.blog_posts import BLOG_POSTS
from src.institutional.presentation.xyron_robot_pages import XYRON_ROBOT_PAGES
from src.institutional.infrastructure.django.templatetags.seo_tags import NOINDEX_ROUTE_NAMES


class InstitutionalRoutesTests(TestCase):
    routes = (
        "home",
        "sistemas_websites_python",
        "livia",
        "camaras_climaticas",
        "manutencao_industrial_campo",
        "ai_video_interaction_platform",
        "xyron",
        "ai_web_solutions_startups",
        "mitsubishi_automacao_industrial",
        "about",
        "services",
        "service_details",
        "blog",
        "blog_list",
        "blog_details",
        "team",
        "team_details",
        "projects",
        "project_details",
        "testimonials",
        "pricing",
        "login",
        "signup",
        "cart",
        "wishlist",
        "checkout",
        "shop",
        "shop_details",
        "faq",
        "contact",
        "error_404_preview",
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


@override_settings(ALLOWED_HOSTS=["testserver", "smartcontrolbrasil.com.br"])
class TechnicalSeoTests(TestCase):
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
            "institutional/js/plugins/meanmenu.min.js",
            "institutional/js/plugins/swiper.min.js",
            "institutional/js/plugins/gsap.js",
            "institutional/js/plugins/ScrollSmoother.js",
            "institutional/js/vendor/magnific-popup.min.js",
            "institutional/js/main.js",
        )

        previous_position = -1
        for script in scripts:
            with self.subTest(script=script):
                tag = f'<script defer src="/static/{script}"></script>'
                position = html.find(tag)
                self.assertGreater(position, previous_position)
                previous_position = position

        self.assertEqual(html.count("institutional/js/vendor/jquery-3.7.1.min.js"), 1)
        self.assertEqual(html.count("institutional/js/main.js"), 1)

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
        self.assertContains(response, 'width="380" height="260" loading="lazy"')

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
        self.assertNotIn(reverse("institutional:pricing"), html)
        self.assertNotIn(reverse("institutional:blog_details"), html)
        self.assertIn(reverse("institutional:manutencao_industrial_campo"), html)
        self.assertIn(reverse("institutional:contact"), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "selecao-controladores-ativos-alta-severidade"}), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "convergencia-robotica-ia-firmwares-dedicados"}), html)
        self.assertIn(reverse("institutional:blog_detail", kwargs={"slug": "eliminar-gargalos-autonomia-previsibilidade"}), html)
        self.assertNotIn("form action=\"#\"", html)


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
        self.assertNotIn(reverse("institutional:team"), html)
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

    def test_services_has_unique_title_description_and_queryless_canonical(self):
        response = self.client.get("/servicos/?utm_source=google&utm_campaign=x&gclid=abc")

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Serviços de Automação Industrial, Robótica e Software | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Conheça os serviços da Smart Control Brasil em automação industrial, robótica, "
            "manutenção técnica, retrofit, integração de sistemas e desenvolvimento web.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/servicos/")
        self.assertNotContains(response, "utm_source")
        self.assertNotContains(response, "utm_campaign")
        self.assertNotContains(response, "gclid")
        self.assertNotContains(response, 'name="robots"')

    def test_blog_article_uses_title_metadata_h1_and_canonical(self):
        response = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        post = BLOG_POSTS["selecao-controladores-ativos-alta-severidade"]
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, f"{post['title']} | Smart Control Brasil")
        self.assertMetaDescription(response, post["meta_description"])
        self.assertCanonical(
            response,
            "https://www.smartcontrolbrasil.com.br/blog/selecao-controladores-ativos-alta-severidade/",
        )
        self.assertEqual(html.count("<h1"), 1)
        self.assertIn(f'<h1 class="breadcrumb__title">{post["title"]}</h1>', html)
        self.assertNotContains(response, 'name="robots"')

    def test_strategic_pages_have_single_descriptive_h1_and_clean_on_page_markers(self):
        expectations = {
            "/xyron/": "Xyron Robotics",
            "/mitsubishi-automacao-industrial/": "Mitsubishi Automação Industrial",
            "/manutencao-industrial-campo/": "Manutenção Industrial",
            "/sistemas-websites-python/": "Sistemas e Websites",
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
                self.assertMetaProperty(
                    response,
                    "og:image",
                    "https://www.smartcontrolbrasil.com.br/static/institutional/imgs/images/banner-6-img-1.png",
                )
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
            "/robotica-educacional/",
            "/robo-seguranca-condominios/",
        )

        for path in disabled_paths:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 404)
                self.assertNotContains(response, '<meta property="og:type" content="website">', status_code=404)
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
                "Soluções de automação industrial Mitsubishi Electric com CLPs, IHMs, inversores, "
                "integração, engenharia e suporte técnico especializado.",
            ),
            (
                "/manutencao-industrial-campo/",
                "Manutenção Industrial e Assistência Técnica | Smart Control Brasil",
                "Manutenção industrial, diagnóstico, assistência técnica em campo, automação, "
                "eletrônica e suporte especializado para máquinas e equipamentos.",
            ),
            (
                "/sistemas-websites-python/",
                "Sistemas Web e Desenvolvimento Python | Smart Control Brasil",
                "Desenvolvimento de sistemas web, plataformas empresariais, automações e soluções "
                "em Python e Django para digitalização de processos.",
            ),
        )

        for path, expected_title, expected_description in metadata_expectations:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertTitle(response, expected_title)
                self.assertMetaDescription(response, expected_description)

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
                self.assertEqual(self.h1_texts(response), [robot["name"]])
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

    def test_internal_links_connect_home_xyron_pages_blog_and_contact(self):
        home = self.client.get("/")
        xyron = self.client.get("/xyron/")
        manutencao = self.client.get("/manutencao-industrial-campo/")
        blog = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")

        self.assertContains(home, 'href="/mitsubishi-automacao-industrial/"')
        self.assertContains(home, 'href="/xyron/"')
        self.assertContains(home, 'href="/sistemas-websites-python/"')
        for robot in XYRON_ROBOT_PAGES:
            self.assertContains(xyron, f'href="/xyron/{robot["slug"]}/"')
        self.assertNotContains(xyron, 'href="/robotica-educacional/"')
        self.assertNotContains(xyron, 'href="/robo-seguranca-condominios/"')
        self.assertNotContains(manutencao, 'href="/camara-climatica/"')
        self.assertContains(blog, 'href="/mitsubishi-automacao-industrial/"')
        self.assertContains(blog, 'href="/contato/"')

    def test_blog_article_includes_article_social_metadata_and_post_image(self):
        response = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        post = BLOG_POSTS["selecao-controladores-ativos-alta-severidade"]
        expected_title = f"{post['title']} | Smart Control Brasil"
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

    def test_blog_article_includes_article_and_breadcrumb_json_ld(self):
        response = self.client.get("/blog/selecao-controladores-ativos-alta-severidade/")
        post = BLOG_POSTS["selecao-controladores-ativos-alta-severidade"]

        articles = self.graph_items(response, "Article")
        breadcrumbs = self.graph_items(response, "BreadcrumbList")

        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article["headline"], post["title"])
        self.assertEqual(article["description"], post["meta_description"])
        self.assertEqual(
            article["url"],
            "https://www.smartcontrolbrasil.com.br/blog/selecao-controladores-ativos-alta-severidade/",
        )
        self.assertEqual(article["image"], f"https://www.smartcontrolbrasil.com.br/static/{post['image']}")
        self.assertEqual(article["author"], {"@type": "Organization", "name": "Smart Control Brasil"})
        self.assertEqual(article["publisher"]["@type"], "Organization")
        self.assertEqual(article["publisher"]["name"], "Smart Control Brasil")
        self.assertNotIn("datePublished", article)
        self.assertNotIn("dateModified", article)
        self.assertEqual(len(breadcrumbs), 1)
        items = breadcrumbs[0]["itemListElement"]
        self.assertEqual([item["position"] for item in items], [1, 2, 3])
        self.assertEqual(items[1]["name"], "Blog")
        self.assertEqual(items[2]["item"], article["url"])

    def test_noindex_page_does_not_render_json_ld(self):
        response = self.client.get("/livia/")

        self.assertEqual(self.structured_data(response), [])

    def test_experimental_demo_route_still_has_noindex_follow(self):
        response = self.client.get("/livia/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex,follow">')
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/livia/")

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
        robot_urls = tuple(
            f"https://www.smartcontrolbrasil.com.br/xyron/{robot['slug']}/"
            for robot in XYRON_ROBOT_PAGES
        )
        for robot_url in robot_urls:
            with self.subTest(robot_url=robot_url):
                self.assertIn(robot_url, urls)
                self.assertEqual(urls.count(robot_url), 1)

        disabled_landing_urls = (
            "https://www.smartcontrolbrasil.com.br/engenharia-serralheria-industrial/",
            "https://www.smartcontrolbrasil.com.br/camara-climatica/",
            "https://www.smartcontrolbrasil.com.br/robotica-educacional/",
            "https://www.smartcontrolbrasil.com.br/robo-seguranca-condominios/",
        )
        for disabled_url in disabled_landing_urls:
            with self.subTest(disabled_url=disabled_url):
                self.assertNotIn(disabled_url, urls)
        self.assertEqual(len(urls), 22 + len(BLOG_POSTS))

        for route_name in NOINDEX_ROUTE_NAMES:
            if route_name == "shop":
                continue
            try:
                path = reverse(f"institutional:{route_name}")
            except Exception:
                continue
            absolute_url = urljoin("https://www.smartcontrolbrasil.com.br", path)
            self.assertNotIn(absolute_url, urls)

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
            "https://www.smartcontrolbrasil.com.br/loja/categoria/robotica/",
            "https://www.smartcontrolbrasil.com.br/loja/categoria/climatizacao/",
            "https://www.smartcontrolbrasil.com.br/loja/categoria/refrigeracao/",
            "https://www.smartcontrolbrasil.com.br/loja/categoria/automacao-industrial/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/littlebot/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/orbit/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/camara-climatica-sob-medida/",
            "https://www.smartcontrolbrasil.com.br/loja/produto/produto-futuro-ativo/",
        }
        for expected_url in expected_urls:
            with self.subTest(expected_url=expected_url):
                self.assertIn(expected_url, urls)

        self.assertNotIn("https://www.smartcontrolbrasil.com.br/loja/produto/produto-inativo/", urls)
        self.assertNotIn("https://www.smartcontrolbrasil.com.br/loja/produto/produto-categoria-inativa/", urls)
        self.assertNotIn("https://www.smartcontrolbrasil.com.br/loja/categoria/categoria-interna/", urls)
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
