from django.views.generic import DetailView

from django_filters.views import FilterView

from bptl.tasks.models import BaseTask

from .filters import TaskFilter


class TaskListView(FilterView):
    template_name = "dashboard/task_list.html"
    filterset_class = TaskFilter
    model = BaseTask
    context_object_name = "tasks"


class TaskDetailView(DetailView):
    template_name = "dashboard/task_detail.html"
    model = BaseTask
    context_object_name = "task"
