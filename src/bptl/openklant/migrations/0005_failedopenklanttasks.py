# Generated by Django 3.2.12 on 2025-05-16 11:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("openklant", "0004_auto_20250404_1333"),
    ]

    operations = [
        migrations.CreateModel(
            name="FailedOpenKlantTasks",
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
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="When the task failed."
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Last updated timestamp."
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        blank=True,
                        help_text="The reason why the task failed, including the exception message.",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("initial", "Queued for retry"),
                            ("failed", "Failed after retry"),
                            ("succeeded", "Succeded after retry"),
                        ],
                        default="initial",
                        help_text="The status of the failed task.",
                        max_length=50,
                    ),
                ),
                (
                    "task",
                    models.OneToOneField(
                        help_text="The OpenKlantInternalTaskModel that failed.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="failed_task",
                        to="openklant.openklantinternaltaskmodel",
                    ),
                ),
            ],
        ),
    ]
