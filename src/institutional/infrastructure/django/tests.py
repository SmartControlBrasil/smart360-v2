from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class InstitutionalRoutesTests(TestCase):
    routes = (
        "home",
        "home_02",
        "home_03",
        "home_04",
        "home_05",
        "home_06",
        "home_07",
        "home_08",
        "home_09",
        "engenharia_serralheria_industrial",
        "home_10",
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

        self.assertTemplateUsed(response, "institutional/demos/index_01.html")
        self.assertContains(response, "institutional/css/main.css")
        self.assertContains(response, "institutional/js/main.js")
        self.assertContains(response, "banner-before")

    def test_menu_contains_original_dropdowns_without_representadas(self):
        response = self.client.get(reverse("institutional:home"))
        expected_labels = (
            "Início",
            "AI Co-Pilot",
            "Gerador de Imagens 3D",
            "Chatbot",
            "Loja com IA",
            "Gerador de Texto com IA",
            "Texto para Vídeo",
            "Agência Digital com IA",
            "SaaS com IA",
            "DALL-E com IA",
            "Gerador de Voz com IA",
            "A Empresa",
            "Serviços",
            "Detalhes do serviço",
            "Blog",
            "Grade do blog",
            "Lista do blog",
            "Detalhes do blog",
            "Páginas",
            "Equipe",
            "Detalhes da equipe",
            "Projetos",
            "Detalhes do projeto",
            "Depoimentos",
            "Planos",
            "Carrinho",
            "Lista de desejos",
            "Checkout",
            "Loja",
            "Detalhes do produto",
            "FAQ",
            "Página 404",
            "Contato",
        )

        for label in expected_labels:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_internal_pages_use_canonical_base(self):
        response = self.client.get(reverse("institutional:about"))

        self.assertTemplateUsed(response, "institutional/base.html")
        self.assertContains(response, "breadcrumb__area")



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
        self.assertContains(response, "Disponivel apos cadastro")

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

    def test_authenticated_public_page_offers_start_button(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="visitor-player", password="strong-pass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("institutional:experience_center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-experience-action=\"start-experience\"")

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
