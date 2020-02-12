from rest_framework import serializers

from ..models import ServiceTask


class WorkUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTask
        fields = ("topic", "vars", "result_variables")
        extra_kwargs = {
            "topic": {"source": "topic_name"},
            "vars": {"source": "variables"},
            "result_variables": {"read_only": True},
        }
