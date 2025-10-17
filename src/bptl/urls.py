from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)
from mozilla_django_oidc_db.views import AdminLoginFailure

from .views import IndexView

handler500 = "bptl.utils.views.server_error"

admin.site.site_header = "bptl admin"
admin.site.site_title = "bptl admin"
admin.site.index_title = "Welcome to the bptl admin"
admin.site.has_permission = lambda request: request.user.is_superuser

urlpatterns = [
    path("hijack/", include("hijack.urls")),
    path("admin/", admin.site.urls),
    path("admin/login/failure/", AdminLoginFailure.as_view(), name="admin-oidc-error"),
    path("tasks/", include("bptl.dashboard.urls")),
    path("taskmappings/", include("bptl.tasks.urls")),
    path("camunda/", include("bptl.camunda.urls")),
    path("schema", SpectacularAPIView.as_view(schema=None), name="api-schema"),
    path(
        "docs/",
        SpectacularRedocView.as_view(url_name="api-schema-json"),
        name="api-docs",
    ),
    path("oidc/", include("mozilla_django_oidc.urls")),
    # Simply show the master template.
    path("", IndexView.as_view(), name="index"),
]


# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run collectstatic). Both the static
# folder and the media folder are only served via Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if settings.DEBUG and apps.is_installed("debug_toolbar"):
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
