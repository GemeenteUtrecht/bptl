from django.contrib import admin

from .models import FetchedTask


@admin.register(FetchedTask)
class FetchedTaskAdmin(admin.ModelAdmin):
    list_display = ("__str__", "priority")
    list_filter = ("topic_name",)
    search_fields = ("task_id", "worker_id")
