from django import forms

import django_filters
from django_filters import FilterSet

from bptl.tasks.models import BaseTask
from bptl.utils.constants import Statuses


class TaskFilter(FilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=Statuses.choices, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = BaseTask
        fields = ("status", "topic_name")
