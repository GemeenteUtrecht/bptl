# Generated by Django 2.2.14 on 2020-12-07 17:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0011_remove_service_extra"),
        ("tasks", "0008_auto_20200228_1616"),
        ("zgw", "0004_auto_20201207_1808"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="DefaultService",
                    fields=[
                        (
                            "id",
                            models.AutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "alias",
                            models.CharField(
                                help_text="Alias for the service used in the particular task",
                                max_length=100,
                                verbose_name="alias",
                            ),
                        ),
                        (
                            "service",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="zgw_consumers.Service",
                            ),
                        ),
                        (
                            "task_mapping",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="tasks.TaskMapping",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "default service",
                        "verbose_name_plural": "default services",
                        "db_table": "tasks_defaultservice",
                        "unique_together": {
                            ("task_mapping", "service"),
                            ("task_mapping", "alias"),
                        },
                    },
                ),
            ],
        ),
        migrations.AlterField(
            model_name="taskmapping",
            name="default_services",
            field=models.ManyToManyField(
                related_name="task_mappings",
                through="tasks.DefaultService",
                to="zgw_consumers.Service",
            ),
        ),
    ]
