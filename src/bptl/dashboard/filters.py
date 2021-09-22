from django import forms
from django.db.models import QuerySet, query

import django_filters
from django_filters import FilterSet

from bptl.camunda.models import ExternalTask
from bptl.tasks.constants import ENGINETYPE_MODEL_MAPPING, EngineTypes
from bptl.tasks.models import BaseTask
from bptl.utils.constants import Statuses


class TaskFilter(FilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=Statuses.choices, widget=forms.CheckboxSelectMultiple
    )
    engine_type = django_filters.MultipleChoiceFilter(
        choices=EngineTypes.choices,
        method="filter_by_type",
        label="Type",
        widget=forms.CheckboxSelectMultiple,
    )
    instance_id = django_filters.CharFilter(
        method="filter_by_process_instance_id",
        label="Process Instance (ID)",
        widget=forms.TextInput,
    )

    class Meta:
        model = BaseTask
        fields = ("status", "topic_name", "engine_type", "instance_id")

    def filter_by_process_instance_id(self, queryset, name, value: str) -> QuerySet:
        if not value:
            return queryset
        qs = queryset.filter(externaltask__instance_id__iexact=value)
        return qs

    def filter_by_type(self, queryset, name, value: list) -> QuerySet:
        if not value:
            return queryset

        qs = queryset.instance_of(ENGINETYPE_MODEL_MAPPING[value[0]])

        if len(value) == 1:
            return qs

        for engine_type in value[1:]:
            qs = qs | queryset.instance_of(ENGINETYPE_MODEL_MAPPING[engine_type])

        return qs
