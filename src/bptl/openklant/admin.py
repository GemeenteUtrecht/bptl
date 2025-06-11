from django.contrib import admin

from polymorphic.admin import PolymorphicChildModelAdmin
from solo.admin import SingletonModelAdmin

from bptl.openklant.models import FailedOpenKlantTasks

from .mail_backend import KCCEmailConfig
from .models import (
    InterneTask,
    OpenKlantActorModel,
    OpenKlantConfig,
    OpenKlantInternalTaskModel,
)


@admin.register(KCCEmailConfig)
class KCCEmailConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(OpenKlantConfig)
class OpenKlantConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(InterneTask)
class InterneTaskAdmin(admin.ModelAdmin):
    list_display = ("__str__",)


@admin.register(OpenKlantActorModel)
class OpenKlantActorAdmin(SingletonModelAdmin):
    pass


@admin.register(OpenKlantInternalTaskModel)
class OpenKlantInternalTaskAdmin(PolymorphicChildModelAdmin):
    list_display = ("__str__", "status")
    list_filter = ("topic_name", "status")
    search_fields = ("task_id", "worker_id")


@admin.register(FailedOpenKlantTasks)
class FailedOpenKlantTasksAdmin(admin.ModelAdmin):
    list_display = ("task", "reason", "created_at", "updated_at")
    search_fields = ("task__id", "reason")
