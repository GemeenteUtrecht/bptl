from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView

from .decorators import superuser_required


@method_decorator(superuser_required, name="dispatch")
class IndexView(TemplateView):
    template_name = "index.html"
