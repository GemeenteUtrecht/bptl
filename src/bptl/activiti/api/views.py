from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.settings import api_settings
from timeline_logger.models import TimelineLog

from bptl.tasks.api import execute

from ..models import ServiceTask
from .serializers import WorkUnitSerializer


class WorkUnitView(CreateAPIView):
    """
    Execute external tasks.

    post:
    Execute task

    Execute external task with specific ``topic``.
    """

    queryset = ServiceTask.objects.all()
    serializer_class = WorkUnitSerializer
    task = None

    @staticmethod
    def execute_task(task: ServiceTask):
        try:
            execute(task)
        except Exception as exc:
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

        # initial logging
        TimelineLog.objects.create(
            content_object=task, extra_data={"status": task.status}
        )

        self.execute_task(task)
