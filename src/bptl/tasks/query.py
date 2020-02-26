from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models

from polymorphic.query import PolymorphicQuerySet


class TaskQuerySet(models.QuerySet):
    def annotate_topics(self) -> "TaskQuerySet":
        """
        Distinctively select the callbacks and annotate the topic names as a list.

        Sets the ``.topics`` attribute.
        """
        qs = self.values("callback").annotate(topics=ArrayAgg("topic_name"))
        return qs


class BaseTaskQuerySet(PolymorphicQuerySet):
    def annotate_status(self):
        qs = (
            self.values("status")
            .annotate(tasks=models.Count("status"))
            .order_by("status")
        )
        return qs
