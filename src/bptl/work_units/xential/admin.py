from django.contrib import admin
from django.template.defaultfilters import urlize
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from bptl.utils.admin import RequestAdminMixin
from bptl.work_units.xential.models import XentialConfiguration


@admin.register(XentialConfiguration)
class XentialConfigurationAdmin(RequestAdminMixin, SingletonModelAdmin):
    readonly_fields = ("get_callback_url",)

    def get_callback_url(self, obj) -> str:
        request = self.get_request()
        full_uri = request.build_absolute_uri(obj.callback_url)
        return urlize(full_uri)

    get_callback_url.short_description = _("Callback URL")
