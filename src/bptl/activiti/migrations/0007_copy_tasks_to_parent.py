from django.db import migrations


def copy_tasks(apps, schema_editor):
    ServiceTask = apps.get_model("activiti.ServiceTask")
    BaseTask = apps.get_model("tasks.BaseTask")
    ContentType = apps.get_model("contenttypes.ContentType")

    contenttype = ContentType.objects.filter(
        app_label="activiti", model="servicetask"
    ).first()
    tasks = ServiceTask.objects.all()
    for activiti_task in tasks:
        base_task = BaseTask.objects.create(
            topic_name=activiti_task.topic_name,
            variables=activiti_task.variables,
            status=activiti_task.status,
            result_variables=activiti_task.result_variables,
            execution_error=activiti_task.execution_error,
            polymorphic_ctype=contenttype,
        )
        base_task.save()
        activiti_task.basetask_ptr = base_task
        activiti_task.save()


class Migration(migrations.Migration):
    dependencies = [("activiti", "0006_servicetask_basetask_ptr")]

    operations = [migrations.RunPython(copy_tasks)]
