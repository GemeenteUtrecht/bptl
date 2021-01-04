from django.urls import path

from .admin_views import TemplatesListView

app_name = "xential"

urlpatterns = [
    path("templates/", TemplatesListView.as_view(), name="templates"),
]
