from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import CoreConfig


@admin.register(CoreConfig)
class CoreConfigAdmin(SingletonModelAdmin):
    pass
