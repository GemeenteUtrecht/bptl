from django.urls import path

from .views import ProcessInstanceListView

app_name = "camunda"

urlpatterns = [
    path(
        "process-instances/",
        ProcessInstanceListView.as_view(),
        name="process-instance-list",
    ),
]
