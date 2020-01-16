from django.contrib import admin

from .models import TaskMapping


@admin.register(TaskMapping)
class TaskMappingAdmin(admin.ModelAdmin):
    model = TaskMapping
    list_display = ("__str__", "active")
    list_filter = ("active",)
    search_fields = ("topic_name", "callback")
