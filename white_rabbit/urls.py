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
    path("", views.HomeView.as_view(), name="home"),
    path(
        "projects/<str:period>",
        views.TotalPerProjectView.as_view(),
        name="projects",
    ),
    path(
        "distribution/<str:period>", views.DistributionView.as_view(), name="categories"
    ),
    path(
        "monthly-hours",
        views.MonthlyWorkingHoursView.as_view(),
        name="monthly-working-hours",
    ),
    path(
        "availability/week",
        views.AvailabilityPerWeekView.as_view(),
        name="week-availability",
    ),
    path(
        "availability/month",
        views.AvailabilityPerMonthView.as_view(),
        name="month-availability",
    ),
    path(
        "suivi-projets",
        views.EstimatedDaysCountView.as_view(),
        name="estimated-days-reporting",
    ),
    path(
        "suivi-projets-complet",
        views.EstimatedDaysCountView.as_view(),
        kwargs={"is_full": True},
        name="estimated-days-reporting-full",
    ),
    path(
        "suivi-monétaire",
        views.FinancialTrackingView.as_view(),
        name="financial-tracking",
    ),
    path("resume", views.ResumeView.as_view()),
    path("alias/", views.AliasView.as_view(), name="alias"),
    path("__debug__/", include(debug_toolbar.urls)),
    # django-hijack
    path(r"hijack/", include("hijack.urls", namespace="hijack")),
    # path('silk/', include('silk.urls', namespace='silk'))
]
