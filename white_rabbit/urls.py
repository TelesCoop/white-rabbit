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
    path("availability/week", views.AvailabilityPerWeekView.as_view()),
    path("availability/month", views.AvailabilityPerMonthView.as_view()),
    path("projects/total", views.TotalPerProjectView.as_view()),
    path("distribution", views.DistributionView.as_view()),
    path("", views.ResumeView.as_view()),
    path("alias/", views.AliasView.as_view()),
    path("__debug__/", include(debug_toolbar.urls)),
    # django-hijack
    path(r"hijack/", include("hijack.urls", namespace="hijack")),
    # path('silk/', include('silk.urls', namespace='silk'))
]
