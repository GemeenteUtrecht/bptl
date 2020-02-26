import collections

from django.db.models import Count
from django.views.generic import ListView

from rest_framework.response import Response
from rest_framework.views import APIView

from bptl.activiti.models import ServiceTask
from bptl.camunda.models import ExternalTask

TASKTYPE_MAPPING = {"camunda": ExternalTask, "activiti": ServiceTask}


def aggregate_data():
    """Return the number of tasks aggregated by statuses"""
    items = []
    counter = collections.Counter()
    for type, model in TASKTYPE_MAPPING.items():
        queryset = (
            model.objects.values("status")
            .annotate(tasks=Count("status"))
            .order_by("status")
        )
        item_data = {q["status"]: q["tasks"] for q in queryset}

        items.append({type: item_data})
        counter.update(item_data)

    return {"items": items, "total": dict(counter)}


class AggregateView(APIView):
    permission_classes = []

    def get(self, request, format=None):
        data = aggregate_data()

        return Response(data)


class TaskListView(ListView):
    template_name = "dashboard/task_list.html"
    queryset = ExternalTask.objects.base_fields("camunda").union(
        ServiceTask.objects.base_fields("activiti")
    )
    context_object_name = "tasks"
