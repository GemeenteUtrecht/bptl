from django.contrib import admin

from .forms import AdminTaskMappingForm
from .models import DefaultService, TaskMapping


class DefaultServiceInline(admin.TabularInline):
    model = DefaultService
    extra = 1


@admin.register(TaskMapping)
class TaskMappingAdmin(admin.ModelAdmin):
    list_display = ("__str__", "active")
    list_filter = ("active",)
    search_fields = ("topic_name", "callback")
    form = AdminTaskMappingForm
    inlines = (DefaultServiceInline,)
