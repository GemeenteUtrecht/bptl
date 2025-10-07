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
    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path("admin/hijack/", include("hijack.urls")),
    path("admin/login/failure/", AdminLoginFailure.as_view(), name="admin-oidc-error"),
    path("admin/", admin.site.urls),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("adfs/", include("django_auth_adfs.urls")),
    # Simply show the master template.
    path("", IndexView.as_view(), name="index"),
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
