from django.views.generic import ListView

from .models import TaskMapping


class TasksView(ListView):
    """
    Display a list of active configured tasks.
    """

    queryset = TaskMapping.objects.filter(active=True)
