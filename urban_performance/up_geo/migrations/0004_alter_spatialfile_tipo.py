# Generated by Django 4.2.11 on 2024-08-13 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('up_geo', '0003_create_default_spatial_files'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spatialfile',
            name='tipo',
            field=models.CharField(choices=[('PB', 'Population Base'), ('HZ', 'Hazard'), ('BF', 'Base Footprint'), ('BT', 'Base Transit'), ('NB', 'NBS'), ('GA', 'Green Area'), ('SP', 'Sports'), ('HO', 'Hospitals'), ('SC', 'Schools'), ('CL', 'Clinics'), ('DC', 'Daycare'), ('IB', 'Infra Base'), ('JB', 'Jobs Base'), ('VB', 'Vegetal Cover Base'), ('PA', 'Permeable Areas Base'), ('AP', 'Additional Population'), ('AF', 'Additional Footprints'), ('AT', 'Additional Transit'), ('ANB', 'Additional NBS'), ('AHO', 'Additional Hospitals'), ('ASC', 'Additional Schools'), ('ASP', 'Additional Sports'), ('ACL', 'Additional Clinics'), ('ADC', 'Additional Daycare'), ('AGA', 'Additional Green Areas'), ('AIN', 'Additional Infra'), ('AJO', 'Additional Jobs'), ('APE', 'Additional Permeable Areas')], max_length=3),
        ),
    ]
