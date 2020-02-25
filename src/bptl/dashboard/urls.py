from django.urls import path

from .views import AggregateView

app_name = "dashboard"

urlpatterns = [
    # Simply show the master template.
    path("aggregate/", AggregateView.as_view(), name="aggregate"),
]
