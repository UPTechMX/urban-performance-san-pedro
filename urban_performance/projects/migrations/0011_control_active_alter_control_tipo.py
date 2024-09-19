# Generated by Django 4.2.11 on 2024-08-15 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_alter_proyecto_estatus'),
    ]

    operations = [
        migrations.AddField(
            model_name='control',
            name='active',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='control',
            name='tipo',
            field=models.CharField(choices=[('BL', 'Base Layer Control'), ('LY', 'Layer Control'), ('SLY', 'Scales Layer Control'), ('SW', 'Switch Control'), ('RG', 'Range Control')], max_length=3),
        ),
    ]
