from typing import List

from django.views.generic import TemplateView

from bptl.utils.admin import StaffRequiredMixin

from .client import XentialClient, get_xential_clients


class TemplatesListView(StaffRequiredMixin, TemplateView):
    template_name = "admin/xential/templates.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        template_groups = []
        xential_clients = get_xential_clients()

        for client in xential_clients:
            template_groups += get_template_groups(client)

        context.update({"template_groups": template_groups})

        return context


def get_name(fields: dict) -> str:
    for field in fields:
        if field["name"] == "name":
            return field["value"]

    return "Geen naam"


def get_template_groups(xential_client: XentialClient) -> List[dict]:
    template_groups_url = "template_utils/getUsableTemplates"
    template_groups_details = xential_client.post(template_groups_url)

    template_groups = []

    for template_group in template_groups_details["objects"]:
        template_group_name = get_name(template_group["fields"])
        template_group_context = {
            "name": template_group_name,
            "api": xential_client.api_root,
            "templates": [],
        }

        templates_details = xential_client.post(
            template_groups_url, params={"parentGroupUuid": template_group["uuid"]}
        )
        for template in templates_details["objects"]:
            template_name = get_name(template["fields"])
            template_group_context["templates"].append(
                {"name": template_name, "uuid": template["uuid"]}
            )

        template_groups.append(template_group_context)

    return template_groups
