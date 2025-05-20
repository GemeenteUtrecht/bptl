from django import forms

from django_celery_beat.models import PeriodicTask


class PatchedPeriodicTaskForm(forms.ModelForm):
    class Meta:
        model = PeriodicTask
        fields = "__all__"  # Explicitly include all fields
