import debug_toolbar
from django.contrib import admin
from django.urls import path, include

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
    path("/home", views.HomeView.as_view()),
    path("projects/<str:period>", views.TotalPerProjectView.as_view(), name="projects"),
    path(
        "distribution/<str:period>", views.DistributionView.as_view(), name="categories"
    ),
    path("availability/week", views.AvailabilityPerWeekView.as_view()),
    path("availability/month", views.AvailabilityPerMonthView.as_view()),
    path(
        "suivi-projets",
        views.EstimatedDaysCountView.as_view(),
        name="estimated-days-reporting",
    ),
    path("", views.ResumeView.as_view()),
    path("alias/", views.AliasView.as_view(), name="alias"),
    path("__debug__/", include(debug_toolbar.urls)),
    # django-hijack
    path(r"hijack/", include("hijack.urls", namespace="hijack")),
    # path('silk/', include('silk.urls', namespace='silk'))
]
