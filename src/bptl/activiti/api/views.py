from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from bptl.tasks.api import execute
from bptl.utils.constants import Statuses

from .serializers import WorkUnitSerializer


class WorkUnitView(APIView):
    serializer = WorkUnitSerializer

    def execute_task(self, task):
        try:
            execute(task)
        except Exception as exc:
            task.status = Statuses.failed
            task.save()

            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: _(
                        "The execution of the task failed with error: {}".format(exc)
                    )
                },
                code="failed-task",
            )

    def post(self, request, *args, **kwargs):
        serializer = self.serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        self.execute_task(task)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
