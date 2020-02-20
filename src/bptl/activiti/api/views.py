from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.settings import api_settings

from bptl.tasks.api import execute
from bptl.utils.constants import Statuses

from ..models import ServiceTask
from .serializers import WorkUnitSerializer


class WorkUnitView(CreateAPIView):
    queryset = ServiceTask.objects.all()
    serializer_class = WorkUnitSerializer
    task = None

    @staticmethod
    def execute_task(task: ServiceTask):
        try:
            execute(task)
        except Exception as exc:
            task.status = Statuses.failed
            task.save()

            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "The execution of the task failed with error: {}"
                    ).format(exc)
                },
                code="failed-task",
            )

    def perform_create(self, serializer):
        task = serializer.save()

        self.execute_task(task)
