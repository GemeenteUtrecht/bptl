# Generated by Django 3.2.12 on 2024-06-28 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camunda", "0015_auto_20210924_1134"),
    ]

    operations = [
        migrations.AlterField(
            model_name="externaltask",
            name="camunda_error",
            field=models.JSONField(
                blank=True, default=None, null=True, verbose_name="camunda error"
            ),
        ),
    ]
