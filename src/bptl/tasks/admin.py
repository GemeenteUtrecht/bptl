from django.contrib import admin

from polymorphic.admin import PolymorphicChildModelFilter, PolymorphicParentModelAdmin

from bptl.camunda.models import ExternalTask
from bptl.openklant.models import OpenKlantInternalTaskModel

from .forms import AdminTaskMappingForm
from .models import BaseTask, DefaultService, TaskMapping


class DefaultServiceInline(admin.TabularInline):
    model = DefaultService
    autocomplete_fields = ("service",)
    extra = 1


@admin.register(TaskMapping)
class TaskMappingAdmin(admin.ModelAdmin):
    list_display = ("__str__", "active")
    list_filter = ("active",)
    search_fields = ("topic_name", "callback")
    form = AdminTaskMappingForm
    inlines = (DefaultServiceInline,)


@admin.register(BaseTask)
class BaseTaskAdmin(PolymorphicParentModelAdmin):
    child_models = (ExternalTask, OpenKlantInternalTaskModel)
    list_filter = (PolymorphicChildModelFilter, "status")
