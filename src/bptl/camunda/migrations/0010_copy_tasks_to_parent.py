from django.db import migrations


def copy_tasks(apps, schema_editor):
    ExternalTask = apps.get_model("camunda.ExternalTask")
    BaseTask = apps.get_model("tasks.BaseTask")
    ContentType = apps.get_model("contenttypes.ContentType")

    contenttype = ContentType.objects.filter(
        app_label="camunda", model="externaltask"
    ).first()
    tasks = ExternalTask.objects.all()
    for camunda_task in tasks:
        base_task = BaseTask.objects.create(
            topic_name=camunda_task.topic_name,
            variables=camunda_task.variables,
            status=camunda_task.status,
            result_variables=camunda_task.result_variables,
            execution_error=camunda_task.execution_error,
            polymorphic_ctype=contenttype,
        )
        base_task.save()
        camunda_task.basetask_ptr = base_task
        camunda_task.save()


class Migration(migrations.Migration):

    dependencies = [
        ("camunda", "0009_externaltask_basetask_ptr"),
        ("tasks", "0007_basetask"),
    ]

    operations = [migrations.RunPython(copy_tasks)]
