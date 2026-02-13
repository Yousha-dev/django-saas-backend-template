"""
URL configuration for the this project.

The `urlpatterns` list routes URLs to views. For more information, see:
https://docs.djangoproject.com/en/5.0/topics/http/urls/

Examples:
1. Function views
    Add an import:  from my_app import views
    Add a URL to urlpatterns:  path('', views.home, name='home')
2. Class-based views
    Add an import:  from other_app.views import Home
    Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
3. Including another URLconf
    Import the include() function: from django.urls import include, path
    Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# Define URL patterns first, without Swagger URLs
api_urlpatterns = [
    path("api/admin/", include("myapp.apis.admin.urls")),
    path("api/auth/", include("myapp.apis.auth.urls")),
    path("api/core/", include("myapp.apis.core.urls")),
    path("api/payment/", include("myapp.apis.payment.urls")),
]

# Then create schema view with the API patterns
schema_view = get_schema_view(
    openapi.Info(
        title="Backend API",
        default_version="v1",
        description="API documentation for the backend.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@duedoom.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=api_urlpatterns,  # Pass API patterns to schema view
)

# Finally, combine API and Swagger URLs
urlpatterns = [
    *api_urlpatterns,
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path(
        "", RedirectView.as_view(url="/swagger/", permanent=False)
    ),  # Optional: redirect root to swagger
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
