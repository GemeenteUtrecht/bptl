from django.urls import path

from .views import TasksView

app_name = "tasks"

urlpatterns = [
    path("", TasksView.as_view(), name="task-list"),
]
