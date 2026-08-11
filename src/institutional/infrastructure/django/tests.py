from pathlib import Path
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import urljoin
from xml.etree import ElementTree

from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from src.institutional.presentation.blog_posts import BLOG_POSTS
from src.institutional.infrastructure.django.templatetags.seo_tags import NOINDEX_ROUTE_NAMES


class InstitutionalRoutesTests(TestCase):
    routes = (
        "home",
        "smart_control_brasil",
        "sistemas_websites_python",
        "livia",
        "camaras_climaticas",
        "manutencao_industrial_campo",
        "ai_video_interaction_platform",
        "xyron",
        "ai_web_solutions_startups",
        "engenharia_serralheria_industrial",
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
        "experience_center",
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

    def test_menu_contains_named_solution_routes(self):
        response = self.client.get(reverse("institutional:home"))
        expected_labels = (
            "Inicio",
            "Sobre",
            "Soluções",
            "Manuteção Industrial",
            "Serralheria Industrial",
            "Mitsubishi Automação",
            "Sistemas e Websites",
            "Xyron Robótica",
            "blog",
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
        self.assertNotContains(response, 'name="robots"')

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

    def test_demo_route_has_noindex_follow(self):
        response = self.client.get("/sistemas-websites-python/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex,follow">')
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/sistemas-websites-python/")

    def test_experience_center_uses_route_metadata_and_is_indexable(self):
        response = self.client.get(reverse("institutional:experience_center"))

        self.assertEqual(response.status_code, 200)
        self.assertTitle(response, "Smart360 Experience Center | Smart Control Brasil")
        self.assertMetaDescription(
            response,
            "Entre no Smart360 Experience Center da Smart Control Brasil e explore experiências "
            "interativas de automação, robótica, tecnologia e inteligência artificial.",
        )
        self.assertCanonical(response, "https://www.smartcontrolbrasil.com.br/experience-center/")
        self.assertNotContains(response, "name=\"robots\"")

    def test_sitemap_returns_public_https_urls_without_noindex_pages(self):
        urls = self.sitemap_urls()

        self.assertIn("https://www.smartcontrolbrasil.com.br/", urls)
        self.assertIn("https://www.smartcontrolbrasil.com.br/engenharia-serralheria-industrial/", urls)
        self.assertEqual(
            urls.count("https://www.smartcontrolbrasil.com.br/engenharia-serralheria-industrial/"),
            1,
        )
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
        self.assertFalse(any("/experience-center/play/" in url for url in urls))
        self.assertFalse(any("/modelos/" in url for url in urls))
        self.assertFalse(any("localhost" in url or "127.0.0.1" in url for url in urls))
        self.assertEqual(len(urls), 9 + len(BLOG_POSTS))

        for route_name in NOINDEX_ROUTE_NAMES:
            try:
                path = reverse(f"institutional:{route_name}")
            except Exception:
                continue
            absolute_url = urljoin("https://www.smartcontrolbrasil.com.br", path)
            self.assertNotIn(absolute_url, urls)

    def test_robots_txt_points_to_production_sitemap_and_blocks_private_paths(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Sitemap: https://www.smartcontrolbrasil.com.br/sitemap.xml")
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /login/")
        self.assertContains(response, "Disallow: /cadastro/")
        self.assertContains(response, "Disallow: /experience-center/play/")



class ExperienceCenterAccessTests(TestCase):
    def test_visitor_accesses_public_landing(self):
        response = self.client.get(reverse("institutional:experience_center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastre-se para jogar")
        self.assertContains(response, "Já tenho uma conta")
        self.assertContains(response, "data-experience-authenticated=\"false\"")

    def test_visitor_does_not_receive_playable_controls_on_landing(self):
        response = self.client.get(reverse("institutional:experience_center"))

        self.assertNotContains(response, "data-experience-id=\"automation-card\"")
        self.assertContains(response, "Disponível após cadastro")

    def test_private_play_route_redirects_visitor_to_login_with_next(self):
        play_url = reverse("institutional:experience_center_play")
        response = self.client.get(play_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("institutional:login"), response["Location"])
        self.assertIn("next=" + play_url, response["Location"])

    def test_authenticated_user_accesses_private_play_route(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="player", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("institutional:experience_center_play"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-experience-authenticated=\"true\"")
        self.assertContains(response, "data-experience-id=\"automation-card\"")
        self.assertContains(response, "Progresso salvo")

    def test_authenticated_public_page_offers_start_link_to_private_route(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="visitor-player", password="strong-pass-123")
        self.client.force_login(user)
        play_url = reverse("institutional:experience_center_play")

        response = self.client.get(reverse("institutional:experience_center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-experience-action=\"start-experience\"")
        self.assertContains(response, f"href=\"{play_url}\"")
        self.assertContains(response, "Começar experiência")

    def test_private_play_route_has_noindex_for_authenticated_user(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="seo-player", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("institutional:experience_center_play"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex,follow">')

    def test_experience_center_play_route_name_remains_valid(self):
        self.assertEqual(reverse("institutional:experience_center_play"), "/experience-center/play/")

    def test_hub_contains_registered_future_experience_cards(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="hub-player", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("institutional:experience_center_play"))

        self.assertEqual(response.status_code, 200)
        for expected in ("spider-robot", "leticia", "marketeiro"):
            with self.subTest(expected=expected):
                self.assertContains(response, expected)
        self.assertContains(response, "Robô-Aranha")
        self.assertContains(response, "Letícia")
        self.assertContains(response, "Marketeiro")
        self.assertContains(response, "Em breve")

    def test_visitor_experience_route_redirects_to_login_with_next(self):
        experience_url = reverse(
            "institutional:experience_center_experience",
            kwargs={"slug": "spider-robot"},
        )
        response = self.client.get(experience_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("institutional:login"), response["Location"])
        self.assertIn("next=" + experience_url, response["Location"])

    def test_authenticated_user_accesses_known_experience_placeholder(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="known-experience", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "institutional:experience_center_experience",
                kwargs={"slug": "spider-robot"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Robô-Aranha")
        self.assertContains(response, "Em breve")
        self.assertContains(response, "Voltar ao hub")
        self.assertNotContains(response, "data-experience-id=\"experience-start\"")

    def test_authenticated_unknown_experience_returns_404(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="unknown-experience", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "institutional:experience_center_experience",
                kwargs={"slug": "unknown-experience"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_private_experience_route_has_noindex_for_authenticated_user(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="private-experience-seo", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "institutional:experience_center_experience",
                kwargs={"slug": "leticia"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<meta name=\"robots\" content=\"noindex,follow\">")

    def test_hub_preserves_javascript_contract_elements(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="contract-player", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("institutional:experience_center_play"))

        for expected in (
            "data-experience-root",
            "data-experience-ui=\"points\"",
            "data-experience-ui=\"level\"",
            "data-experience-ui=\"missions-panel\"",
            "data-experience-ui=\"achievement\"",
            "data-experience-ui=\"score-feedback\"",
            "data-experience-id=\"automation-card\"",
            "data-experience-id=\"robotics-card\"",
            "data-experience-id=\"systems-interaction\"",
            "data-experience-id=\"meet-liro\"",
        ):
            with self.subTest(expected=expected):
                self.assertContains(response, expected)

    def test_login_next_points_to_experience_play_route(self):
        play_url = reverse("institutional:experience_center_play")
        response = self.client.get(reverse("institutional:login") + f"?next={play_url}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"name=\"next\" value=\"{play_url}\"")

    def test_signup_authenticates_and_redirects_to_private_route_by_default(self):
        response = self.client.post(
            reverse("institutional:signup"),
            {
                "username": "signup-player",
                "password1": "SenhaTeste123!Segura",
                "password2": "SenhaTeste123!Segura",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("institutional:experience_center_play"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_signup_respects_safe_next_parameter(self):
        play_url = reverse("institutional:experience_center_play")
        response = self.client.post(
            reverse("institutional:signup"),
            {
                "username": "signup-next-player",
                "password1": "SenhaTeste123!Segura",
                "password2": "SenhaTeste123!Segura",
                "next": play_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, play_url)

    def test_login_rejects_external_next_and_redirects_to_private_route(self):
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
        self.assertRedirects(response, reverse("institutional:experience_center_play"))

    def test_logout_post_ends_user_session(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="logout-player",
            password="SenhaTeste123!Segura",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("institutional:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("institutional:experience_center"))
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_javascript_has_auth_guards_for_points_and_persistence(self):
        state_js = Path("static/institutional/js/experience-center/experience-state.js").read_text()
        storage_js = Path("static/institutional/js/experience-center/experience-storage.js").read_text()
        controller_js = Path("static/institutional/js/experience-center/experience-center.js").read_text()

        self.assertIn("function isAuthenticated()", state_js)
        self.assertIn("experience:auth-required", state_js)
        self.assertIn("if (!isAuthenticated())", storage_js)
        self.assertIn("function requireAuth", controller_js)
