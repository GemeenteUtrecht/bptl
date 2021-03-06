# Generated by Django 2.2.14 on 2020-11-16 16:00

from django.db import migrations


def move_brpconfig_to_default_services(apps, schema_editor):
    BRPConfig = apps.get_model("brp", "BRPConfig")
    DefaultService = apps.get_model("zgw", "DefaultService")
    App = apps.get_model("credentials", "App")
    AppServiceCredentials = apps.get_model("credentials", "AppServiceCredentials")
    TaskMapping = apps.get_model("tasks", "TaskMapping")

    if not BRPConfig.objects.filter(service__isnull=False).exists():
        return

    service = BRPConfig.objects.get().service
    task_mappings = TaskMapping.objects.filter(
        callback__startswith="bptl.work_units.brp.",
    ).exclude(default_services=service)

    # migrate the credentials to a placeholder app
    app, created = App.objects.get_or_create(app_id="BRP_MIGRATION_FIXME")
    AppServiceCredentials.objects.create(
        app=app,
        service=service,
        client_id=service.client_id,
        secret=service.secret,
        header_key=service.header_key,
        header_value=service.header_value,
    )

    for task_mapping in task_mappings:
        DefaultService.objects.create(
            task_mapping=task_mapping, service=service, alias="brp"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("brp", "0004_auto_20201102_1103"),
        ("zgw", "0002_move_zgw_tasks"),
        ("credentials", "0001_initial"),
        ("tasks", "0008_auto_20200228_1616"),
    ]

    operations = [
        migrations.RunPython(
            move_brpconfig_to_default_services, migrations.RunPython.noop
        ),
    ]
