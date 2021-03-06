# Generated by Django 2.2.14 on 2020-12-07 10:50

from django.db import migrations

from zgw_consumers.constants import APITypes, AuthTypes

from bptl.tasks.registry import register

from ..tasks import retrieve_openbare_ruimten
from ..utils import ALIAS

API_ROOT = "https://brt.basisregistraties.overheid.nl/api/v2/"


def create_brt_service(apps, schema_editor):
    Service = apps.get_model("zgw_consumers", "Service")
    Service.objects.get_or_create(
        api_root=API_ROOT,
        defaults={
            "label": "Basisregistratie Topografie (BRT)",
            "api_type": APITypes.orc,
            "auth_type": AuthTypes.api_key,
            "oas": API_ROOT,
        },
    )


def add_service_to_task_mappings(apps, schema_editor):
    Service = apps.get_model("zgw_consumers", "Service")
    TaskMapping = apps.get_model("tasks", "TaskMapping")
    DefaultService = apps.get_model("zgw", "DefaultService")

    brt = Service.objects.get(api_root=API_ROOT)

    dotted_path = register.get_for(retrieve_openbare_ruimten)
    for task_mapping in TaskMapping.objects.filter(callback=dotted_path):
        DefaultService.objects.get_or_create(
            task_mapping=task_mapping, service=brt, defaults={"alias": ALIAS}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0011_remove_service_extra"),
        ("tasks", "0008_auto_20200228_1616"),
        ("zgw", "0003_auto_20201112_1547"),
    ]

    operations = [
        migrations.RunPython(create_brt_service, migrations.RunPython.noop),
        migrations.RunPython(add_service_to_task_mappings, migrations.RunPython.noop),
    ]
