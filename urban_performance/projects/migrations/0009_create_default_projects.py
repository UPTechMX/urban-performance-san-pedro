# Generated by Django 4.2.11 on 2024-05-28 14:36

import os, shutil
from django.db import migrations

from urban_performance.projects.models import (
    ProyectoStatus,
    assumptions_path,
    controls_path,
    create_defaults,
)
from urban_performance.projects.models import Proyecto as ProjectModel


def insert_default_projects(apps, schema_editor):
    return


def backwards(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0008_proyecto_visibilidad_publica"),
        ("users", "0002_create_user"),
    ]

    operations = [
        migrations.RunPython(insert_default_projects, backwards),
    ]
