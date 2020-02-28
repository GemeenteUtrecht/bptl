# Generated by Django 2.2.10 on 2020-02-26 13:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activiti", "0005_servicetask_execution_error"),
        ("tasks", "0007_basetask"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicetask",
            name="basetask_ptr",
            field=models.OneToOneField(
                auto_created=True,
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                serialize=False,
                to="tasks.BaseTask",
                null=True,
            ),
            preserve_default=False,
        ),
    ]
