from django.contrib import admin

from polymorphic.admin import PolymorphicChildModelAdmin

from .models import CronTask


@admin.register(CronTask)
class CronTaskAdmin(PolymorphicChildModelAdmin):
    list_display = ("__str__", "status")
    list_filter = ("topic_name", "status")
