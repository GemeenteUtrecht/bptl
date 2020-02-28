from django.urls import path

from .views import AggregateView

app_name = "dashboard-api"

urlpatterns = [
    # Simply show the master template.
    path("aggregate/", AggregateView.as_view(), name="aggregate"),
]
