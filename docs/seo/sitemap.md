# Sitemap XML e robots.txt

## Implementacao

O sitemap fica em `src/institutional/presentation/sitemaps.py` e e registrado em
`config/urls.py` na URL publica `/sitemap.xml`.

Ele usa `django.contrib.sitemaps` e e composto por:

- `StaticViewSitemap`: paginas institucionais publicas e indexaveis.
- `BlogPostSitemap`: artigos do blog definidos em `BLOG_POSTS`.
- `AuthorSitemap`: paginas de autor em `AUTHORS`.
- `CommerceStaticSitemap`: pagina principal da loja (`/loja/`).
- `CommerceCategorySitemap`: categorias ativas indexaveis (exclui `NOINDEX_CATEGORY_SLUGS`).
- `CommerceProductSitemap`: produtos ativos (exclui slugs com pagina institucional canonica).

## URLs incluidas

Entram no sitemap paginas publicas relevantes para SEO, como:

- Home, empresa, servicos, contato
- Engenharia e servicos: Servicos Eletricos, Ar-Condicionado, Refrigeração Comercial, Manutencao Industrial, Mitsubishi Automação, Sistemas Web/Python, SEO/Presença Digital e Tráfego Pago e Orgânico
- Xyron Robotics, robos individuais e pilares tematicos
- Blog, artigos e autores
- Loja e produtos/categorias indexaveis

Para adicionar uma nova pagina institucional estatica, inclua a rota em
`STATIC_PUBLIC_ROUTES` em `sitemaps.py`.

## URLs excluidas

Nao entram rotas administrativas, autenticacao, cadastro, legacy com redirect,
demos de template, categorias da loja marcadas como `noindex`, produtos com
pagina institucional canonica (ex.: Little Bot, Orbit) e previews tecnicos.

Exemplos fora do sitemap:

- `/login/`, `/cadastro/`, `/admin/`, `/painel/`
- Legacy SEO (`/sobre/`, `/faq/`, `/parceiros/...`, `/projetos/...`)
- `/loja/detalhes/` (redirect permanente para `/loja/`)
- Categorias `noindex`: automacao-industrial, climatizacao, refrigeracao, robotica

## Blog

Os artigos atuais sao estaticos e vivem em
`src/institutional/presentation/blog_posts.py`. Para adicionar um novo artigo ao
sitemap, inclua o slug em `BLOG_POSTS` **e** a entrada correspondente em
`BLOG_POST_EDITORIAL` (`blog_editorial.py`), usada para `lastmod`; a URL sera
gerada por `institutional:blog_detail`.

Cluster recente de ar-condicionado (indexaveis):

- `/blog/infraestrutura-correta-ar-condicionado/`
- `/blog/preventiva-corretiva-ar-condicionado/`
- `/blog/eletrica-climatizacao-comercial/`
- `/blog/vazamento-fluido-refrigerante/`

## Robots

O `robots.txt` e servido em `/robots.txt` pela view `robots_txt`. Ele bloqueia
areas tecnicas/privadas e declara:

`Sitemap: https://www.smartcontrolbrasil.com.br/sitemap.xml`

O dominio vem de `PUBLIC_SITE_URL`, configuravel por variavel de ambiente. O
padrao do projeto e `https://www.smartcontrolbrasil.com.br`.

## Validacao local

Execute:

```bash
python manage.py check
python manage.py test src.institutional.infrastructure.django.tests.TechnicalSeoTests.test_sitemap_returns_public_https_urls_without_noindex_pages
```

Depois acesse `/sitemap.xml` e `/robots.txt` usando o host de producao ou um
host permitido em `DJANGO_ALLOWED_HOSTS`.
