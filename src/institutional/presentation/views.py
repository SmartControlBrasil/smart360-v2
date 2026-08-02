from django.http import Http404
from django.shortcuts import render

from src.institutional.application.get_home_page import GetHomePage
from src.institutional.presentation.blog_posts import BLOG_POSTS, BLOG_POSTS_LIST


def home(request):
    page = GetHomePage().execute()
    return render(
        request,
        "institutional/demos/index_01.html",
        {"page": page},
    )


def home_02(request):
    return render(request, "institutional/demos/index_02.html")


def home_03(request):
    return render(request, "institutional/demos/index_03.html")


def home_04(request):
    return render(request, "institutional/demos/index_04.html")


def home_05(request):
    return render(request, "institutional/demos/index_05.html")


def home_06(request):
    return render(request, "institutional/demos/index_06.html")


def home_07(request):
    return render(request, "institutional/demos/index_07.html")


def home_08(request):
    return render(request, "institutional/demos/index_08.html")


def home_09(request):
    return render(request, "institutional/demos/index_09.html")


def engenharia_serralheria_industrial(request):
    return render(request, "institutional/demos/index_09.html")


def home_10(request):
    return render(request, "institutional/demos/index_10.html")


def about(request):
    return render(request, "institutional/pages/about.html")


def services(request):
    return render(request, "institutional/pages/service.html")


def service_details(request):
    return render(request, "institutional/pages/service_details.html")


def blog(request):
    return render(
        request,
        "institutional/pages/blog.html",
        {"blog_posts": BLOG_POSTS_LIST},
    )


def blog_list(request):
    return render(request, "institutional/pages/blog_list.html")


def blog_detail(request, slug):
    post = BLOG_POSTS.get(slug)
    if post is None:
        raise Http404("Artigo tecnico nao encontrado.")

    related_posts = [
        {"slug": related_slug, **related_post}
        for related_slug, related_post in BLOG_POSTS.items()
        if related_slug != slug
    ][:3]

    return render(
        request,
        "institutional/pages/blog_detail.html",
        {
            "post": {"slug": slug, **post},
            "related_posts": related_posts,
        },
    )


def blog_details(request):
    return blog_detail(request, "selecao-controladores-ativos-alta-severidade")


def team(request):
    return render(request, "institutional/pages/team.html")


def team_details(request):
    return render(request, "institutional/pages/team_details.html")


def projects(request):
    return render(request, "institutional/pages/project.html")


def project_details(request):
    return render(request, "institutional/pages/project_details.html")


def testimonials(request):
    return render(request, "institutional/pages/testimonial.html")


def pricing(request):
    return render(request, "institutional/pages/pricing.html")


def cart(request):
    return render(request, "institutional/pages/cart.html")


def wishlist(request):
    return render(request, "institutional/pages/wishlist.html")


def checkout(request):
    return render(request, "institutional/pages/checkout.html")


def shop(request):
    return render(request, "institutional/pages/shop.html")


def shop_details(request):
    return render(request, "institutional/pages/shop_details.html")


def faq(request):
    return render(request, "institutional/pages/faq.html")


def contact(request):
    return render(request, "institutional/pages/contact.html")


def error_404_preview(request):
    return render(request, "institutional/pages/error_404.html")
