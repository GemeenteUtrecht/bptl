from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import ZACConfig


@admin.register(ZACConfig)
class ZacConfigAdmin(SingletonModelAdmin):
    pass
