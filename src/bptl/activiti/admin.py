from django.contrib import admin

from polymorphic.admin import PolymorphicChildModelAdmin
from solo.admin import SingletonModelAdmin

from .models import ActivitiConfig, ServiceTask


@admin.register(ActivitiConfig)
class ActivitiConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(ServiceTask)
class ServiceTaskAdmin(PolymorphicChildModelAdmin):
    list_display = ("topic_name", "status")
    list_filter = ("topic_name", "status")
