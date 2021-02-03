from django.urls import path

from .views import DocumentCreationCallbackView, InteractiveDocumentView

app_name = "Xential"

urlpatterns = [
    path(
        "xential_callbacks",
        DocumentCreationCallbackView.as_view(),
        name="xential-callbacks",
    ),
    path(
        "interactive_document/<uuid:uuid>/<str:token>",
        InteractiveDocumentView.as_view(),
        name="interactive-document",
    ),
]
