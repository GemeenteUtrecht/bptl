# Generated by Django 3.2.12 on 2024-06-28 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0010_auto_20201207_1818"),
    ]

    operations = [
        migrations.AlterField(
            model_name="basetask",
            name="result_variables",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="basetask",
            name="variables",
            field=models.JSONField(default=dict),
        ),
    ]
