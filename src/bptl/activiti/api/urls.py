from django.conf.urls import include, url
from django.urls import path

from .views import WorkUnitView

urlpatterns = [
    url(
        r"^v(?P<version>\d+)/",
        include([path("work-unit", WorkUnitView.as_view(), name="work-unit")]),
    )
]
