from django.contrib import admin

from .forms import TaskMappingForm
from .models import TaskMapping


@admin.register(TaskMapping)
class TaskMappingAdmin(admin.ModelAdmin):
    list_display = ("__str__", "active")
    list_filter = ("active",)
    search_fields = ("topic_name", "callback")
    form = TaskMappingForm
