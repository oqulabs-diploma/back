# Generated by Django 5.0.6 on 2024-08-01 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_attachment_comment_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='attachment',
            field=models.CharField(max_length=1000),
        ),
    ]
