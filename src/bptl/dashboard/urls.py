from django.urls import include, path

from .views import TaskDetailView, TaskListView

app_name = "dashboard"

urlpatterns = [
    # Simply show the master template.
    path("", TaskListView.as_view(), name="task-list"),
    path("<pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("api/", include("bptl.dashboard.api.urls")),
]
