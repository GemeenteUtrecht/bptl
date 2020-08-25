from django.urls import path

from .views import CallbackView

app_name = "valid_sign"

urlpatterns = [
    path("callbacks", CallbackView.as_view(), name="callbacks"),
]
