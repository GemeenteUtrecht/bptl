from django.urls import path

from .views import AddTaskView, TasksView

app_name = "tasks"

urlpatterns = [
    path("", TasksView.as_view(), name="task-list"),
    path("add/", AddTaskView.as_view(), name="task-create"),
]
