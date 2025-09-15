import debug_toolbar
from django.contrib import admin
from django.urls import path, include

from . import settings
from white_rabbit.views.auth_view import MyLoginView
from white_rabbit.views.home_view import HomeView
from white_rabbit.views.availability_view import (
    AvailabilityPerWeekView,
    AvailabilityPerMonthView,
    MonthlyWorkingHoursView,
    WeeklyWorkingHoursView,
)
from white_rabbit.views.project_view import (
    AliasView,
    ResumeView,
    TotalPerProjectView,
    DistributionView,
    EstimatedDaysCountView,
    FinancialTrackingView,
)
from white_rabbit.views.gantt_view import GanttView

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
    path("", HomeView.as_view(), name="home"),
    path(
        "projects/<str:period>",
        TotalPerProjectView.as_view(),
        name="projects",
    ),
    path("distribution/<str:period>", DistributionView.as_view(), name="categories"),
    path(
        "monthly-hours",
        MonthlyWorkingHoursView.as_view(),
        name="monthly-working-hours",
    ),
    path(
        "weekly-hours",
        WeeklyWorkingHoursView.as_view(),
        name="weekly-working-hours",
    ),
    path(
        "availability/week",
        AvailabilityPerWeekView.as_view(),
        name="week-availability",
    ),
    path(
        "availability/month",
        AvailabilityPerMonthView.as_view(),
        name="month-availability",
    ),
    path(
        "suivi-projets",
        EstimatedDaysCountView.as_view(),
        name="estimated-days-reporting",
    ),
    path(
        "suivi-projets-complet",
        EstimatedDaysCountView.as_view(),
        kwargs={"is_full": True},
        name="estimated-days-reporting-full",
    ),
    path(
        "suivi-monétaire",
        FinancialTrackingView.as_view(),
        name="financial-tracking",
    ),
    path("resume", ResumeView.as_view()),
    path("alias/", AliasView.as_view(), name="alias"),
    path("gantt/", GanttView.as_view(), name="gantt"),
    path("__debug__/", include(debug_toolbar.urls)),
    # django-hijack
    path(r"hijack/", include("hijack.urls", namespace="hijack")),
    # path('silk/', include('silk.urls', namespace='silk'))
]

if settings.DEBUG and settings.BROWSER_RELOAD:
    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
