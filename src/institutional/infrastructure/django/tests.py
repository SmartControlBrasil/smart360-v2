from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_returns_successfully(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)

    def test_home_uses_expected_template(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertTemplateUsed(response, "institutional/home.html")

    def test_home_contains_primary_heading(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertContains(
            response,
            "Tecnologia aplicada a resultados reais",
        )

    def test_home_contains_seo_metadata(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertContains(
            response,
            "<title>Smart Control Brasil | Automação, Robótica e Sistemas</title>",
            html=True,
        )
        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, 'name="description"')
