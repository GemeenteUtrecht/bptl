from django.urls import path

from .views import AddTaskMappingView, TaskMappingsView

app_name = "tasks"

urlpatterns = [
    path("", TaskMappingsView.as_view(), name="taskmapping-list"),
    path("add/", AddTaskMappingView.as_view(), name="taskmapping-create"),
]
