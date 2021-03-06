# Generated by Django 2.2.10 on 2020-02-28 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0007_basetask"),
    ]

    operations = [
        migrations.AlterField(
            model_name="basetask",
            name="status",
            field=models.CharField(
                choices=[
                    ("initial", "Initial"),
                    ("in_progress", "In progress"),
                    ("performed", "Performed"),
                    ("failed", "Failed"),
                    ("completed", "Completed"),
                ],
                default="initial",
                help_text="The current status of task processing",
                max_length=50,
                verbose_name="status",
            ),
        ),
    ]
