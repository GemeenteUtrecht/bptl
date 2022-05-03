from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from django_filters.views import FilterView

from bptl.tasks.models import BaseTask

from ..decorators import superuser_required
from .filters import TaskFilter


@method_decorator(superuser_required, name="dispatch")
class TaskListView(FilterView):
    template_name = "dashboard/task_list.html"
    filterset_class = TaskFilter
    queryset = BaseTask.objects.all().order_by("-pk")
    context_object_name = "tasks"
    paginate_by = 20


@method_decorator(superuser_required, name="dispatch")
class TaskDetailView(DetailView):
    template_name = "dashboard/task_detail.html"
    model = BaseTask
    context_object_name = "task"
