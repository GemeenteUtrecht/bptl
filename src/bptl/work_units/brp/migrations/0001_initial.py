# Generated by Django 2.2.10 on 2020-03-12 10:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BRPConfig",
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
                    "api_root",
                    models.URLField(
                        default="https://brp.example.com",
                        help_text="Root URL if BRP api",
                        verbose_name="API-root",
                    ),
                ),
                (
                    "header_key",
                    models.CharField(
                        blank=True,
                        help_text="HTTP Authorization header name, required if the API is not open.",
                        max_length=100,
                        verbose_name="header key",
                    ),
                ),
                (
                    "header_value",
                    models.CharField(
                        blank=True,
                        help_text="HTTP Authorization header value, required if the API is not open.",
                        max_length=255,
                        verbose_name="header value",
                    ),
                ),
            ],
            options={"verbose_name": "BRP Configuration",},
        ),
    ]