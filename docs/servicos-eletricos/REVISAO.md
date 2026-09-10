# Serviços Elétricos — revisão manual

Implementação local em `/servicos-eletricos/`, nome Django `institutional:servicos_eletricos`. Sem commit, push ou deploy.

## Auditoria e integração

O projeto usa `src/institutional/presentation` para views, URLs e sitemap; templates em `templates/institutional`; assets locais em `static/institutional`. As páginas de manutenção e automação usam layouts derivados de `institutional/base.html`. As páginas Xyron usam a mesma base e o submenu oficial. O blog tem conteúdo real, mas foi adotado o FAQ solicitado.

`base.html` concentra metadados via `seo_tags`, Google Analytics/Ads, configuração Lívia, WhatsApp, header e footer. Esses componentes foram herdados, sem acrescentar tags Google ou widgets. Os CTAs apontam para contato, rotas industriais existentes e o mesmo WhatsApp do componente oficial. Eventos primários usam `data-track-event`, `data-track-location` e `data-track-label` existentes.

O template original `smart360v2_baixado/index-3.html` foi preservado. Seus 77 caminhos de assets existem no diretório original; veja `assets-template.txt`. `main.css` já contém os estilos de banner3, chatbot, features, pricing, explore-apps, things, credible, marketing e further-2. A adaptação reutiliza essa sequência e seus componentes, substituindo os conteúdos SaaS/IA por elétrica. Foram removidos preços, assinaturas, depoimentos e logos sem fundamentação.

O layout global já fornece Bootstrap, jQuery, MeanMenu e GSAP. Não foram adicionadas bibliotecas, fontes, Swiper, WOW, Magnific Popup ou Tilt. O vídeo usa um popup nativo `dialog`, com fechamento por Escape, botão e clique fora, restauração de foco e remoção do iframe ao fechar. A rolagem nativa nesta página dispensa ScrollSmoother: dois blocos de atributos na base preservam os IDs originais por padrão para todas as outras páginas.

## Arquivos criados

- `templates/institutional/pages/servicos-eletricos.html`: página baseada nas seções do index-3, herdando a base oficial.
- `src/institutional/presentation/electrical_services.py`: conteúdo, FAQ e referências de mídia.
- `static/institutional/css/servicos-eletricos.css`: ajustes restritos à página e ao popup.
- `static/institutional/js/servicos-eletricos.js`: interação do vídeo, carregado sob clique.
- `static/institutional/icons/electrical/{energia,quadro,ferramentas,projeto}.svg`: quatro ícones técnicos vetoriais locais.
- `src/institutional/infrastructure/django/test_electrical_services.py`: seis testes da nova página e configuração de vídeo.
- `docs/servicos-eletricos/`: relatório e inventário de assets.

## Arquivos modificados

- `config/settings/base.py`: configuração `ELECTRICAL_SERVICES_VIDEO_URL` por ambiente.
- `src/institutional/presentation/views.py`: view e validação de URL YouTube.
- `src/institutional/presentation/urls.py`: nova rota.
- `src/institutional/presentation/sitemaps.py`: inclusão da página pública.
- `src/institutional/infrastructure/django/templatetags/seo_tags.py`: metadados, breadcrumb, Service e FAQPage.
- `src/institutional/infrastructure/django/tests.py`: expectativas do novo menu e nova entrada do sitemap.
- `templates/institutional/base.html`: pontos de extensão para rolagem nativa, mantendo o padrão anterior.
- `templates/institutional/partials/header.html`: submenu Engenharia e Serviços.

## Assets e vídeo

Reutilizados: `institutional/imgs/images/painel-eletrico.webp` (hero, 590×408); `institutional/imgs/images/retrofite-painel-eletronico.webp` (thumbnail, 930×470); ícones locais next/check/play/close/whatsapp; CSS, JS, logo e footer oficiais. As duas imagens foram inspecionadas visualmente. Nenhuma imagem remota ou imagem sintética foi adicionada.

As imagens IA/chatbot `hero-3-img.png`, `feature-img-1.png`, os ícones chatbot e os logos de apps do template original não são usados na nova página. Não há caminhos de imagem quebrados deliberadamente. As fotos locais podem ser substituídas por fotos específicas de serviços elétricos, caso desejado; não são necessárias para renderizar a página.

Pendente obrigatório: fornecer URL aprovada do vídeo institucional. Thumbnail exclusiva também pode ser fornecida. Trocar `HERO_IMAGE` / `VIDEO_THUMBNAIL` em `electrical_services.py` para novos arquivos locais e ajustar suas dimensões no template/SEO quando necessário.

URL provisória original: `https://www.youtube.com/watch?v=DZLlw5BNQ3g`. Usada apenas em DEBUG e identificada como prévia. Bloqueada com DEBUG=False, inclusive se configurada por engano. Configurar `ELECTRICAL_SERVICES_VIDEO_URL=https://www.youtube.com/watch?v=ID_APROVADO` (ou URL youtu.be). Sem configuração em produção, o bloco mantém imagem, play e popup com mensagem de vídeo em breve e CTA de contato. Nenhum iframe é carregado antes do clique.

## SEO, menu e links

Title: Serviços Elétricos em São Paulo | Smart Control Brasil.
Description: Serviços elétricos residenciais, comerciais e industriais em São Paulo. Instalações, manutenção, quadros, projetos e soluções com suporte de engenharia.

Um H1, H2/H3 semânticos; canonical limpo de parâmetros pelo helper existente; Open Graph e Twitter com imagem local do painel. JSON-LD: Service, BreadcrumbList e FAQPage, com as mesmas sete perguntas/respostas visíveis. Sem novo schema global de Organization/LocalBusiness. Sitemap contém a nova URL.

Menu: Soluções → Engenharia e Serviços → Serviços Elétricos / Manutenção Industrial / Automação Industrial. O ramo Xyron permanece intacto e usa o mecanismo responsivo existente. Ar-Condicionado e Refrigeração Comercial ficam documentados em comentário para inclusão quando houver rotas próprias, inexistentes na auditoria.

Links internos: `/contato/`, `/manutencao-industrial-campo/`, `/mitsubishi-automacao-industrial/`, `/` no breadcrumb e `/servicos/` no menu. Nenhuma rota fictícia foi criada.

## Testes

`manage.py check`: System check identified no issues (0 silenced).

Comando da suíte relevante:

```sh
.venv/bin/python manage.py test src.institutional.infrastructure.django.tests.InstitutionalRoutesTests src.institutional.infrastructure.django.tests.TechnicalSeoTests src.institutional.infrastructure.django.tests.ConversionTrackingTests src.institutional.infrastructure.django.test_electrical_services --settings=config.settings.base --noinput
```

99 testes executados; 97 passaram, 2 falharam. Os seis testes novos passaram. SQLite temporário de testes via settings.base; não foi usado o banco PostgreSQL de desenvolvimento.

As duas falhas foram reproduzidas isoladamente em uma cópia do HEAD anterior em `/tmp/electrical-baseline`, sem as alterações desta tarefa:

- `test_xyron_pillar_pages_use_base_assets_without_optional_plugins`: espera 4 stylesheets, encontra 3.
- `test_xyron_robot_pages_have_single_h1_metadata_breadcrumb_and_sitemap`: Waiter Bot espera a imagem `services-7-04.png`, ausente no HTML anterior também.

Essas falhas preexistentes não foram alteradas por estarem fora do escopo. Logs locais: `/tmp/electrical-tests-final.log` e `/tmp/electrical-baseline.log`.

Playwright/Chromium: HTTP 200, um H1 e ausência de overflow horizontal em 1440×1000, 1920×1080, 768×1024 e 390×844. FAQ abre; play abre o dialog; Escape fecha. Screenshots em `/tmp/electrical-{largura}.png`. Foram bloqueadas requisições externas na validação: carregamento real do YouTube, recebimento de eventos Google e conexão ao backend da Lívia não foram testados. A configuração herdada desses serviços foi preservada.

Verificação adicional do menu nas quatro resoluções: abertura de Engenharia e Serviços e Xyron, link LIRO acessível, hamburger apenas em tablet/mobile e ausência de overflow. Todas as imagens foram carregadas antes da checagem final, sem falhas. Capturas do menu em `/tmp/electrical-menu-{largura}.png`.

## Estado Git

Veja `git-state.txt` para as saídas de `git diff --stat` e `git status --short`. O diff --stat padrão não inclui os arquivos novos ainda não rastreados; estes aparecem no status e na lista acima. `git diff --check` passou.

Aguardando revisão manual; nenhuma publicação foi executada.
