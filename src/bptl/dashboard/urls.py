from django.urls import path

from .views import AggregateView, TaskDetailView, TaskListView

app_name = "dashboard"

urlpatterns = [
    # Simply show the master template.
    path("", TaskListView.as_view(), name="task-list"),
    path("<pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("aggregate/", AggregateView.as_view(), name="aggregate"),
]
