# Generated by Django 5.0.6 on 2025-02-23 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0043_enrollmenttask_ai_used_screenshots"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
            ],
        ),
    ]
