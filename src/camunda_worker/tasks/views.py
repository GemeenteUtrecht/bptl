from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView

from .forms import TaskMappingForm
from .models import TaskMapping


class TasksView(ListView):
    """
    Display a list of active configured tasks.
    """

    queryset = TaskMapping.objects.filter(active=True).annotate_topics()
    context_object_name = "tasks"


class AddTaskView(LoginRequiredMixin, CreateView):
    model = TaskMapping
    form_class = TaskMappingForm
