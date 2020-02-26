from django.db import models
from django.db.models import CharField, Value


class BaseTaskQuerySet(models.QuerySet):
    def base_fields(self, type) -> "BaseTaskQuerySet":
        """
        Select only fields, which exists in BaseTask abstract class
        """
        qs = self.values(
            "id",
            "topic_name",
            "variables",
            "status",
            "result_variables",
            "execution_error",
        ).annotate(type=Value(type, output_field=CharField()))
        return qs
