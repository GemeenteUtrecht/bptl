from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import ActivitiConfig


@admin.register(ActivitiConfig)
class ActivitiConfigAdmin(SingletonModelAdmin):
    pass
