# Generated by Django 4.2.11 on 2024-08-23 20:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_proyecto_niveles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proyecto',
            name='niveles',
            field=models.JSONField(default={}),
        ),
    ]
