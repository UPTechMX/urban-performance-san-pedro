# Generated by Django 4.2.11 on 2024-04-26 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicador',
            name='unidad',
            field=models.CharField(default='unit', max_length=30),
        ),
        migrations.AlterField(
            model_name='control',
            name='tipo',
            field=models.CharField(choices=[('BL', 'Base Layer Control'), ('LY', 'Layer Control'), ('SW', 'Switch Control'), ('RG', 'Range Control')], max_length=2),
        ),
    ]
