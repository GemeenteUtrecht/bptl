# Generated by Django 3.2.12 on 2025-03-25 11:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('openklant', '0002_auto_20250324_1236'),
    ]

    operations = [
        migrations.RenameField(
            model_name='openklantinternaltaskmodel',
            old_name='task_uuid',
            new_name='task_id',
        ),
    ]
