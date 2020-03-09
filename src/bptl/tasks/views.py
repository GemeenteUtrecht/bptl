from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import DefaultServiceFormset, TaskMappingForm
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

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["defaultservices"] = DefaultServiceFormset(self.request.POST)
        else:
            data["defaultservices"] = DefaultServiceFormset()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        defaultservices = context["defaultservices"]

        if defaultservices.is_valid():
            self.object = form.save()
            defaultservices.instance = self.object
            defaultservices.save()

        return super().form_valid(form)
