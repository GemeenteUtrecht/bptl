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

    def get_formset(self):
        data = self.request.POST if self.request.method == "POST" else None
        return DefaultServiceFormset(data=data)

    def get_context_data(self, **kwargs):
        formset = kwargs.pop("formset", self.get_formset())
        kwargs["formset"] = formset

        context = super().get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)

        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )
