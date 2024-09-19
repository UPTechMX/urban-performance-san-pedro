from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext_lazy as _

from urban_performance.projects import models as projects_models

import os

fss = FileSystemStorage()


class SpatialOpts(models.TextChoices):
    # BASE
    POPULATION_BASE = "PB", _("Population Base")
    BASE_FOOTPRINT = "BF", _("Base Footprint")
    BASE_TRANSIT = "BT", _("Base Transit")
    NBS = "NB", _("NBS")
    GREEN_AREA = "GA", _("Green Area")
    SPORTS = "SP", _("Sports")
    HOSPITALS = "HO", _("Hospitals")
    SCHOOLS = "SC", _("Schools")
    CLINICS = "CL", _("Clinics")
    DAYCARE = "DC", _("Daycare")
    INFRA_BASE = "IB", _("Infra Base")
    JOBS_BASE = "JB", _("Jobs Base")
    VEGETAL_COVER_BASE = "VB", _("Vegetal Cover Base")
    PERMEABLE_AREAS_BASE = "PA", _("Permeable Areas Base")
    ROADS_BASE = "RB", _("Roads Base")
    HAZARD = "HZ", _("Hazard")

    # ADDITIONALS
    ADDITIONAL_POPULATION = "AP", _("Additional Population")
    ADDITIONAL_FOOTPRINTS = "AF", _("Additional Footprints")
    ADDITIONAL_TRANSIT = "AT", _("Additional Transit")
    ADDITIONAL_NBS = "ANB", _("Additional NBS")
    ADDITIONAL_HOSPITALS = "AHO", _("Additional Hospitals")
    ADDITIONAL_SCHOOLS = "ASC", _("Additional Schools")
    ADDITIONAL_SPORTS = "ASP", _("Additional Sports")
    ADDITIONAL_CLINICS = "ACL", _("Additional Clinics")
    ADDITIONAL_DAYCARE = "ADC", _("Additional Daycare")
    ADDITIONAL_UGA = "AGA", _("Additional Green Areas")
    ADDITIONAL_INFRA = "AIN", _("Additional Infra")
    ADDITIONAL_JOBS = "AJO", _("Additional Jobs")
    ADDITIONAL_PERMEABLE_AREAS = "APE", _("Additional Permeable Areas")



def spatial_path(instance, filename):
    path_map = {
        SpatialOpts.POPULATION_BASE: "projects/{0}/base/PB_poblacion_base.geojson",
        SpatialOpts.BASE_FOOTPRINT: "projects/{0}/base/BF_area_urbana_base.geojson",
        SpatialOpts.BASE_TRANSIT: "projects/{0}/base/BT_lineas_transporte_base.geojson",
        SpatialOpts.NBS: "projects/{0}/base/nbs_base.geojson",
        SpatialOpts.GREEN_AREA: "projects/{0}/base/GA_areas_verdes_base.geojson",
        SpatialOpts.SPORTS: "projects/{0}/base/SP_centros_deportivos_base.geojson",
        SpatialOpts.HOSPITALS: "projects/{0}/base/HO_hospitales_base.geojson",
        SpatialOpts.SCHOOLS: "projects/{0}/base/SC_escuelas_base.geojson",
        SpatialOpts.CLINICS: "projects/{0}/base/CL_centro_salud_base.geojson",
        SpatialOpts.DAYCARE: "projects/{0}/base/DC_guarderia_base.geojson",
        SpatialOpts.INFRA_BASE: "projects/{0}/base/infraestructura_base.geojson",
        SpatialOpts.JOBS_BASE: "projects/{0}/base/empleos_base.geojson",
        SpatialOpts.VEGETAL_COVER_BASE: "projects/{0}/base/VB_cobertura_vegetal.geojson",
        SpatialOpts.PERMEABLE_AREAS_BASE: "projects/{0}/base/areas_permeables_base.geojson",
        SpatialOpts.ROADS_BASE: "projects/{0}/base/RB_roads_base.geojson",
        SpatialOpts.HAZARD: "projects/{0}/hazard/HZ_inundaciones_disuelta.geojson",

        SpatialOpts.ADDITIONAL_POPULATION: "projects/{0}/population/{1}",
        SpatialOpts.ADDITIONAL_FOOTPRINTS: "projects/{0}/footprints/{1}",
        SpatialOpts.ADDITIONAL_TRANSIT: "projects/{0}/transit/{1}",
        SpatialOpts.ADDITIONAL_NBS: "projects/{0}/nbs/{1}",
        SpatialOpts.ADDITIONAL_HOSPITALS: "projects/{0}/hospitals/{1}",
        SpatialOpts.ADDITIONAL_SCHOOLS: "projects/{0}/schools/{1}",
        SpatialOpts.ADDITIONAL_SPORTS: "projects/{0}/sports/{1}",
        SpatialOpts.ADDITIONAL_CLINICS: "projects/{0}/clinics/{1}",
        SpatialOpts.ADDITIONAL_DAYCARE: "projects/{0}/daycare/{1}",
        SpatialOpts.ADDITIONAL_UGA: "projects/{0}/green areas/{1}",
        SpatialOpts.ADDITIONAL_INFRA: "projects/{0}/infraestructure/{1}",
        SpatialOpts.ADDITIONAL_JOBS: "projects/{0}/employment/{1}",
        SpatialOpts.ADDITIONAL_PERMEABLE_AREAS: "projects/{0}/permeable areas/{1}",
    }
    path = path_map[instance.tipo].format(instance.proyecto.uuid, filename)
    if fss.exists(path):
        os.remove(os.path.join(settings.MEDIA_ROOT, path))
    return path


class SpatialFile(models.Model):
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(
        max_length=3,
        choices=SpatialOpts.choices,
    )
    descripcion = models.TextField(null=True, blank=True)
    archivo = models.FileField(upload_to=spatial_path)
    proyecto = models.ForeignKey(projects_models.Proyecto, on_delete=models.CASCADE)
    creado_el = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.tipo}: {self.nombre}"
