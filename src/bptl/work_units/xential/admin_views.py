from django.views.generic import TemplateView

from bptl.tasks.models import DefaultService
from bptl.utils.admin import StaffRequiredMixin

from .client import ALIAS


class TemplatesListView(StaffRequiredMixin, TemplateView):
    template_name = "admin/xential/templates.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        templates = []
        # find xential services using alias and Default Services
        xential_services = (
            DefaultService.objects.filter(alias=ALIAS).values("service").distinct()
        )
        for service in xential_services:
            # use default auth headers, since we don't know APP_ID
            xential_client = service.build_client()
            list_url = "xential/templates"
            list_response = xential_client.get(list_url)
            templates[service] = list_response["data"]["templates"]

        context.update({"templates": templates})

        return context
