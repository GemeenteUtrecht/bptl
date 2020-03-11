from django.conf.urls import include, url
from django.urls import path, re_path
from django.views.generic import RedirectView

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .views import WorkUnitView

schema_view = get_schema_view(
    openapi.Info(
        title="BP Task Library API",
        default_version="v1",
        description="An API to approach BPTL work units",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    url(
        r"^v(?P<version>\d+)/",
        include(
            [
                path("", RedirectView.as_view(pattern_name="schema-redoc")),
                # real api
                path("work-unit", WorkUnitView.as_view(), name="work-unit"),
                # OAS
                re_path(
                    r"^openapi(?P<format>\.json|\.yaml)$",
                    schema_view.without_ui(cache_timeout=0),
                    name="schema-json",
                ),
                re_path(
                    r"^swagger/$",
                    schema_view.with_ui("swagger", cache_timeout=0),
                    name="schema-swagger-ui",
                ),
                re_path(
                    r"^redoc/$",
                    schema_view.with_ui("redoc", cache_timeout=0),
                    name="schema-redoc",
                ),
            ]
        ),
    )
]
