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
