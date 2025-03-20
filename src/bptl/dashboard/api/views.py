from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils import timezone

from rest_framework.response import Response
from rest_framework.views import APIView
from timeline_logger.models import TimelineLog

from bptl.tasks.engine_mapping import ENGINETYPE_MODEL_MAPPING
from bptl.utils.constants import Statuses

TASK_STATUS_HISTORY = timedelta(hours=24)


def aggregate_data(since: datetime):
    """Return the number of tasks aggregated by statuses"""

    models = ENGINETYPE_MODEL_MAPPING.values()
    content_types = ContentType.objects.get_for_models(*models)
    ct_id_to_model = {ct.id: model for model, ct in content_types.items()}
    model_to_engine_type = {
        model: engine_type for engine_type, model in ENGINETYPE_MODEL_MAPPING.items()
    }

    log_entries = (
        TimelineLog.objects.filter(
            content_type__in=content_types.values(),
            extra_data__status__in=Statuses.values,
            timestamp__gte=since,
        )
        .distinct("object_id")
        .order_by("object_id", "-timestamp")
    )

    total_data = defaultdict(int)
    items = defaultdict(lambda: defaultdict(int))

    # separate qs because annotate + distinct is not possible
    qs = (
        TimelineLog.objects.filter(pk__in=log_entries)
        .values("extra_data__status", "content_type_id")
        .annotate(tasks=Count("extra_data__status"))
    )

    for count in qs:
        status = count["extra_data__status"]
        model = ct_id_to_model[count["content_type_id"]]
        engine_type = model_to_engine_type[model]

        items[engine_type][status] += count["tasks"]
        total_data[status] += count["tasks"]

    if not total_data:
        total_data = {status: 0 for status in Statuses.values.keys()}
        items = {
            engine_type: total_data for engine_type in ENGINETYPE_MODEL_MAPPING.keys()
        }

    return {
        "since": since,
        "items": items,
        "total": total_data,
    }


class AggregateView(APIView):
    swagger_schema = None

    permission_classes = []

    def get(self, request, format=None):
        now = timezone.now()
        data = aggregate_data(since=now - TASK_STATUS_HISTORY)
        return Response(data)
