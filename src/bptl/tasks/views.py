from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import TaskMappingForm
from .models import TaskMapping


class TaskMappingsView(ListView):
    """
    Display a list of active configured tasks.
    """

    queryset = TaskMapping.objects.filter(active=True).annotate_topics()
    context_object_name = "task_mappings"


class AddTaskMappingView(LoginRequiredMixin, CreateView):
    model = TaskMapping
    form_class = TaskMappingForm
    success_url = reverse_lazy("tasks:taskmapping-list")
