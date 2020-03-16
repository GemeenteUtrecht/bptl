from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import BRPConfig


@admin.register(BRPConfig)
class BRPConfigAdmin(SingletonModelAdmin):
    pass
