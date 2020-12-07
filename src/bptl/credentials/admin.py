from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import App, AppServiceCredentials


class AppServiceCredentialsInline(admin.TabularInline):
    model = AppServiceCredentials
    fields = ("service", "client_id", "secret", "header_key", "header_value")
    autocomplete_fields = ("service",)
    extra = 1


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("label", "app_id")
    search_fields = ("app_id", "label")
    inlines = [AppServiceCredentialsInline]


@admin.register(AppServiceCredentials)
class AppServiceCredentialsAdmin(admin.ModelAdmin):
    list_display = ("app", "service")
    list_filter = ("app", "service__auth_type", "service")
    fieldsets = (
        (
            None,
            {
                "fields": ("app", "service"),
            },
        ),
        (
            _("ZGW credentials (JWT)"),
            {
                "fields": ("client_id", "secret"),
            },
        ),
        (
            _("API-key credentials"),
            {
                "fields": ("header_key", "header_value"),
            },
        ),
    )
