from django.views.generic import DetailView

from django_filters.views import FilterView
from rest_framework.response import Response
from rest_framework.views import APIView

from bptl.tasks.constants import ENGINETYPE_MODEL_MAPPING
from bptl.tasks.models import BaseTask

from .filters import TaskFilter


def aggregate_data():
    """Return the number of tasks aggregated by statuses"""
    items = []
    for type, model in ENGINETYPE_MODEL_MAPPING.items():
        item_qs = BaseTask.objects.instance_of(model).annotate_status()
        item_data = {q["status"]: q["tasks"] for q in item_qs}
        items.append({type: item_data})

    total_qs = BaseTask.objects.annotate_status()
    total_data = {q["status"]: q["tasks"] for q in total_qs}

    return {"items": items, "total": total_data}


class AggregateView(APIView):
    permission_classes = []

    def get(self, request, format=None):
        data = aggregate_data()

        return Response(data)


class TaskListView(FilterView):
    template_name = "dashboard/task_list.html"
    filterset_class = TaskFilter
    model = BaseTask
    context_object_name = "tasks"


class TaskDetailView(DetailView):
    template_name = "dashboard/task_detail.html"
    model = BaseTask
    context_object_name = "task"
