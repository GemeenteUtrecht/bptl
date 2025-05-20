from django.contrib import admin

from django_celery_beat.models import PeriodicTask
from solo.admin import SingletonModelAdmin

from .forms import PatchedPeriodicTaskForm
from .models import CoreConfig

# Unregister the existing PeriodicTaskAdmin
try:
    admin.site.unregister(PeriodicTask)
except KeyError:
    pass


@admin.register(PeriodicTask)
class PatchedPeriodicTaskAdmin(admin.ModelAdmin):
    form = PatchedPeriodicTaskForm


@admin.register(CoreConfig)
class CoreConfigAdmin(SingletonModelAdmin):
    pass
