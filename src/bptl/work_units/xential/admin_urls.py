from django.urls import path

from .admin_views import TemplatesListView

app_name = "xential"

urlpatterns = [
    path(r"templates", TemplatesListView.as_view(), name="templates"),
]
