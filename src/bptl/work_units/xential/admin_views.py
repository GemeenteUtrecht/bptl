from django.views.generic import TemplateView

from bptl.utils.admin import StaffRequiredMixin

from .client import get_xential_client


class TemplatesListView(StaffRequiredMixin, TemplateView):
    template_name = "admin/xential/templates.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        template_groups = []
        template_groups_url = "template_utils/getUsableTemplates"
        xential_client = get_xential_client()

        template_groups_details = xential_client.post(template_groups_url)
        for template_group in template_groups_details["objects"]:
            template_group_name = get_name(template_group["fields"])
            template_group_context = {"name": f"{template_group_name}", "templates": []}

            templates_details = xential_client.post(
                template_groups_url, params={"parentGroupUuid": template_group["uuid"]}
            )
            for template in templates_details["objects"]:
                template_name = get_name(template["fields"])
                template_group_context["templates"].append(
                    {"name": template_name, "uuid": template["uuid"]}
                )

            template_groups.append(template_group_context)

        context.update({"template_groups": template_groups})

        return context


def get_name(fields: dict) -> str:
    for field in fields:
        if field["name"] == "name":
            return field["value"]

    return "Geen naam"
