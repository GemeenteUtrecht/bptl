from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import ActivitiConfig, ServiceTask


@admin.register(ActivitiConfig)
class ActivitiConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(ServiceTask)
class ServiceTaskAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status")
    list_filter = ("topic_name", "status")
