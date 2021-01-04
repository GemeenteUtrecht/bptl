from django.views.generic import TemplateView

from bptl.utils.admin import StaffRequiredMixin

from .client import get_default_clients


class TemplatesListView(StaffRequiredMixin, TemplateView):
    template_name = "admin/xential/templates.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        template_groups = {}
        list_url = "xential/templates"
        xential_clients = get_default_clients()
        for client in xential_clients:
            list_response = client.get(list_url)
            template_groups[client.api_root] = list_response["data"]["templates"]

        context.update({"template_groups": template_groups})

        return context
