# Sitemap XML e robots.txt

## Implementacao

O sitemap fica em `src/institutional/presentation/sitemaps.py` e e registrado em
`config/urls.py` na URL publica `/sitemap.xml`.

Ele usa `django.contrib.sitemaps` e e composto por:

- `StaticViewSitemap`: paginas institucionais publicas e indexaveis.
- `BlogPostSitemap`: artigos do blog definidos em `BLOG_POSTS`.

## URLs incluidas

Entram no sitemap apenas paginas publicas relevantes para SEO, como home,
servicos, solucao de engenharia/serralheria industrial, projetos, blog, artigos,
empresa, depoimentos, FAQ e contato.

## URLs excluidas

Nao entram rotas administrativas, autenticacao, cadastro, demos de template,
rotas privadas do Experience Center, carrinho, checkout, loja e previews
tecnicos.

## Blog

Os artigos atuais sao estaticos e vivem em
`src/institutional/presentation/blog_posts.py`. Para adicionar um novo artigo ao
sitemap, inclua o slug em `BLOG_POSTS`; a URL sera gerada por
`institutional:blog_detail`.

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
python manage.py test src.institutional.infrastructure.django
```

Depois acesse `/sitemap.xml` e `/robots.txt` usando o host de producao ou um
host permitido em `DJANGO_ALLOWED_HOSTS`.
