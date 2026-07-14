from django.shortcuts import render

from src.institutional.application.get_home_page import GetHomePage


def home(request):
    page = GetHomePage().execute()

    return render(
        request,
        "institutional/home.html",
        {"page": page},
    )
