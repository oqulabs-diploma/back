# Generated by Django 5.0.6 on 2025-02-23 13:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0044_tasktype"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="task_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="app.tasktype",
            ),
        ),
    ]
