from django.urls import path

from .views import ProcessDefinitionListView, ProcessInstanceListView

app_name = "camunda"

urlpatterns = [
    path(
        "process-instances/",
        ProcessInstanceListView.as_view(),
        name="process-instance-list",
    ),
    path(
        "process-definitions/",
        ProcessDefinitionListView.as_view(),
        name="process-definition-list",
    ),
]
