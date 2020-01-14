from django.contrib import admin
from django.utils import timezone

from .models import FetchedTask


@admin.register(FetchedTask)
class FetchedTaskAdmin(admin.ModelAdmin):
    list_display = ("__str__", "priority", "is_expired")
    list_filter = ("topic_name", "lock_expires_at")
    search_fields = ("task_id", "worker_id")

    def is_expired(self, obj) -> bool:
        if obj.lock_expires_at is None:
            return False
        return obj.lock_expires_at <= timezone.now()

    is_expired.boolean = True
