from django.contrib import admin
from django.urls import path, include
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from . import views
from .views import MyLoginView

urlpatterns = [
    path("configuration/", admin.site.urls),
    path(
        r"auth/login/",
        MyLoginView.as_view(
            extra_context={
                "site_header": "Lapin Blanc",
            }
        ),
    ),
    path("auth/", include("django.contrib.auth.urls")),
    path("", cache_page(60)(vary_on_cookie(views.HomeView.as_view()))),
    path("", views.HomeView.as_view()),
]
