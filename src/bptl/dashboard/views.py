import collections

from django.db.models import Count

from rest_framework.response import Response
from rest_framework.views import APIView

from bptl.activiti.models import ServiceTask
from bptl.camunda.models import ExternalTask


class AggregateView(APIView):
    permission_classes = []

    def get(self, request, format=None):
        """
        Return the number of tasks aggregated by statuses
        """
        # union() doesn't support annotate(), so the final aggregation is done in python datatypes
        counter = collections.Counter()
        for model in [ExternalTask, ServiceTask]:
            queryset = (
                model.objects.values("status")
                .annotate(tasks=Count("status"))
                .order_by("status")
            )
            data = {q["status"]: q["tasks"] for q in queryset}
            counter.update(data)

        return Response(dict(counter))
