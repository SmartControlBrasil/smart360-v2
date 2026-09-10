import json
import re

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from src.institutional.presentation.electrical_services import FAQS, DEVELOPMENT_VIDEO_URL


class ElectricalServicesTests(SimpleTestCase):
    def test_page_metadata_visible_faq_and_integrations(self):
        response = self.client.get(reverse('institutional:servicos_eletricos') + '?utm_source=test')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(len(re.findall(r'<h1\b', html)), 1)
        self.assertContains(response, 'Serviços Elétricos em São Paulo | Smart Control Brasil')
        self.assertContains(response, 'rel="canonical" href="https://www.smartcontrolbrasil.com.br/servicos-eletricos/"')
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))['@graph']
        self.assertCountEqual([node['@type'] for node in graph], ['BreadcrumbList', 'Service', 'FAQPage'])
        faq = next(node for node in graph if node['@type'] == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), len(FAQS))
        for question, answer in FAQS:
            self.assertIn(f'<h3>{question}</h3>', html)
            self.assertIn(f'<p>{answer}</p>', html)
        for name in ('contact', 'manutencao_industrial_campo', 'mitsubishi_automacao_industrial'):
            self.assertIn(reverse('institutional:' + name), html)
        self.assertContains(response, 'id="livia-config"', count=1)
        self.assertNotContains(response, 'plugins/ScrollSmoother.js')
        self.assertNotContains(response, 'id="smooth-wrapper"')

    @override_settings(DEBUG=False, ELECTRICAL_SERVICES_VIDEO_URL='')
    def test_production_keeps_popup_without_template_video(self):
        response = self.client.get('/servicos-eletricos/')
        self.assertContains(response, 'data-electrical-video')
        self.assertContains(response, 'Nosso vídeo institucional estará disponível em breve.')
        self.assertNotContains(response, 'DZLlw5BNQ3g')

    @override_settings(DEBUG=True, ELECTRICAL_SERVICES_VIDEO_URL='')
    def test_development_preview_is_labelled(self):
        response = self.client.get('/servicos-eletricos/')
        self.assertContains(response, 'Prévia de desenvolvimento')
        self.assertContains(response, 'youtube-nocookie.com/embed/DZLlw5BNQ3g')

    @override_settings(DEBUG=False, ELECTRICAL_SERVICES_VIDEO_URL='https://youtu.be/abcdefghijk')
    def test_configured_youtube_url_loads_only_on_interaction(self):
        response = self.client.get('/servicos-eletricos/')
        self.assertContains(response, 'data-embed-url="https://www.youtube-nocookie.com/embed/abcdefghijk?autoplay=1"')
        self.assertNotContains(response, '<iframe')

    @override_settings(DEBUG=False, ELECTRICAL_SERVICES_VIDEO_URL='https://untrusted.example/watch?v=DZLlw5BNQ3g')
    def test_untrusted_embed_is_not_rendered(self):
        response = self.client.get('/servicos-eletricos/')
        self.assertContains(response, 'data-embed-url=""')
        self.assertNotContains(response, 'untrusted.example')

    @override_settings(DEBUG=False, ELECTRICAL_SERVICES_VIDEO_URL=DEVELOPMENT_VIDEO_URL)
    def test_template_video_is_blocked_even_if_configured_in_production(self):
        response = self.client.get('/servicos-eletricos/')
        self.assertContains(response, 'data-embed-url=""')
        self.assertNotContains(response, 'DZLlw5BNQ3g')
