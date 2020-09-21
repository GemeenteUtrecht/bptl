from dataclasses import dataclass

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from django_camunda.client import get_client


@dataclass
class ProcessInstance:
    id: str
    business_key: str
    definition_id: str
    definition_name: str


def get_process_instances():
    camunda = get_client()
    instances = camunda.get("process-instance")

    definitions = camunda.get(
        "process-definition",
    )

    definition_names = {
        definition["id"]: definition["name"] or definition["key"]
        for definition in definitions
    }
    return [
        ProcessInstance(
            id=instance["id"],
            business_key=instance["business_key"],
            definition_id=instance["definition_id"],
            definition_name=definition_names[instance["definition_id"]],
        )
        for instance in instances
    ]


class ProcessInstanceListView(UserPassesTestMixin, TemplateView):
    template_name = "camunda/process_instance_list.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["process_instances"] = get_process_instances()
        return context

    def post(self, request, *args, **kwargs):
        camunda = get_client()
        ids = request.POST.getlist("_delete")
        camunda.post(
            "process-instance/delete",
            json={
                "processInstanceIds": ids,
                "deleteReason": f"BPTL initiated delete by {request.user}",
                "skipCustomListeners": True,
                "skipSubprocesses": False,
                "failIfNotExists": False,
            },
        )
        return redirect("camunda:process-instance-list")
