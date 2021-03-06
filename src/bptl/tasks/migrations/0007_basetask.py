# Generated by Django 2.2.10 on 2020-02-26 13:41

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("tasks", "0006_taskmapping_default_services"),
    ]

    operations = [
        migrations.CreateModel(
            name="BaseTask",
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
                    "topic_name",
                    models.CharField(
                        help_text="Topics determine which functions need to run for a task.",
                        max_length=255,
                        verbose_name="topic name",
                    ),
                ),
                (
                    "variables",
                    django.contrib.postgres.fields.jsonb.JSONField(default=dict),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("initial", "Initial"),
                            ("in_progress", "In progress"),
                            (
                                "performed",
                                "The task is performed, but not sent to Camunda",
                            ),
                            ("failed", "Failed"),
                            ("completed", "Completed"),
                        ],
                        default="initial",
                        help_text="The current status of task processing",
                        max_length=50,
                        verbose_name="status",
                    ),
                ),
                (
                    "result_variables",
                    django.contrib.postgres.fields.jsonb.JSONField(default=dict),
                ),
                (
                    "execution_error",
                    models.TextField(
                        blank=True,
                        help_text="The error that occurred during execution.",
                        verbose_name="execution error",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_tasks.basetask_set+",
                        to="contenttypes.ContentType",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
    ]
