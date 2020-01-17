from django.contrib import admin

from .models import FetchedTask


@admin.register(FetchedTask)
class FetchedTaskAdmin(admin.ModelAdmin):
    list_display = ("__str__", "priority", "is_expired", "status")
    list_filter = ("topic_name", "lock_expires_at", "status")
    search_fields = ("task_id", "worker_id")

    def is_expired(self, obj) -> bool:
        return obj.is_expired

    is_expired.boolean = True
