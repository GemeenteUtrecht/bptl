from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models


class TaskQuerySet(models.QuerySet):
    def annotate_topics(self) -> "TaskQuerySet":
        """
        Distinctively select the callbacks and annotate the topic names as a list.

        Sets the ``.topics`` attribute.
        """
        qs = self.values("callback").annotate(topics=ArrayAgg("topic_name"))
        return qs
