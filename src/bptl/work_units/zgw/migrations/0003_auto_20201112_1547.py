# Generated by Django 2.2.14 on 2020-11-12 14:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0011_remove_service_extra"),
        ("tasks", "0008_auto_20200228_1616"),
        ("zgw", "0002_move_zgw_tasks"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="defaultservice",
            unique_together={("task_mapping", "alias"), ("task_mapping", "service")},
        ),
    ]
