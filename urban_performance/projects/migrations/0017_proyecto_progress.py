# Generated by Django 4.2.11 on 2024-09-14 19:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0016_proyecto_partial_processing'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='progress',
            field=models.SmallIntegerField(default=0),
        ),
    ]
