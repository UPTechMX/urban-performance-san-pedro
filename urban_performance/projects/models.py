from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext_lazy as _
import os
import uuid

fss = FileSystemStorage()

User = get_user_model()


class ControlOpts(models.TextChoices):
    BASE_LAYER = "BL", _("Base Layer Control")
    LAYER = "LY", _("Layer Control")
    SCALES_LAYER = "SLY", _("Scales Layer Control")
    SWITCH = "SW", _("Switch Control")
    RANGE = "RG", _("Range Control")


class ProyectoStatus(models.TextChoices):
    PROCESSING = "PR", _("Processing proyect")
    READY = "RD", _("Ready to use")
    ERROR = "ER", _("Error")


def assumptions_path(instance, filename):
    path = "projects/{0}/assumptions/assumptions_SP.csv".format(instance.uuid)
    if fss.exists(path):
        os.remove(os.path.join(settings.MEDIA_ROOT, path))
    return path


def controls_path(instance, filename):
    path = "projects/{0}/Controls.csv".format(instance.uuid)
    if fss.exists(path):
        os.remove(os.path.join(settings.MEDIA_ROOT, path))
    return path


# Create your models here.
class Proyecto(models.Model):
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assumptions = models.FileField(upload_to=assumptions_path)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    ciudad = models.CharField(max_length=100)
    uso_como_template = models.BooleanField(default=False)
    creado_el = models.DateTimeField(auto_now_add=True)
    estatus = models.CharField(
        max_length=2,
        choices=ProyectoStatus.choices,
        default=ProyectoStatus.PROCESSING,
    )
    controles = models.FileField(blank=True, null=True, upload_to=controls_path)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    visibilidad_publica = models.BooleanField(default=False)
    niveles = models.JSONField(default=dict)
    partial_processing = models.JSONField(default=dict)
    progress = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = (
            "ciudad",
            "creado_por",
        )

    def get_folder_path(self):
        return f"{settings.MEDIA_ROOT}/projects/{self.pk}/"

    def __str__(self):
        return f"{self.nombre}"


class Control(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    campo = models.CharField(max_length=100)
    tipo = models.CharField(
        max_length=3,
        choices=ControlOpts.choices,
    )
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.tipo}: {self.nombre}"


class Indicador(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    campo = models.CharField(max_length=100)
    unidad = models.CharField(max_length=30, default="unit")

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.campo}: {self.nombre}"


class Escenario(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    structure = models.JSONField()
    nombre = models.CharField(max_length=100)
    posicion = models.IntegerField(default=1)
    descripcion = models.TextField()

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.nombre}"


def create_defaults(project_instance):
    default_controles = [
        {
            "nombre": "Population",
            "descripcion": "Population",
            "campo": "population_",
            "tipo": "SLY",
            "active": True,
        },
        {
            "nombre": "Urban Expansion",
            "descripcion": "Urban Expansion",
            "campo": "footprint",
            "tipo": "LY",
        },
        {
            "nombre": "Public Transit",
            "descripcion": "Public Transit",
            "campo": "transit",
            "tipo": "LY",
            "active": True,
        },
        {
            "nombre": "Risk Mitigation",
            "descripcion": "Risk Mitigation",
            "campo": "nbs",
            "tipo": "LY",
            "active": True,
        },
        {
            "nombre": "Residential Energy Efficiency",
            "descripcion": "Residential energy efficiency",
            "campo": "energy_efficiency",
            "tipo": "RG",
        },
        {
            "nombre": "Solar Energy Coverage",
            "descripcion": "Solar Energy Coverage",
            "campo": "solar_energy",
            "tipo": "RG",
        },
        {
            "nombre": "Rainwater harvesting",
            "descripcion": "Rainwater harvesting",
            "campo": "rwh",
            "tipo": "RG",
        },
        {
            "nombre": "Hospitals",
            "descripcion": "Hospitals",
            "campo": "hospitals",
            "tipo": "LY",
        },
        {
            "nombre": "Schools",
            "descripcion": "Schools",
            "campo": "schools",
            "tipo": "LY",
        },
        {
            "nombre": "Sport Centers",
            "descripcion": "Sport Centers",
            "campo": "sport_centers",
            "tipo": "LY",
        },
        {
            "nombre": "Clinics",
            "descripcion": "Clinics",
            "campo": "clinics",
            "tipo": "LY",
        },
        {
            "nombre": "Daycare",
            "descripcion": "Daycare",
            "campo": "daycare",
            "tipo": "LY",
        },
        {
            "nombre": "Urban Green Areas",
            "descripcion": "Urban Green Areas",
            "campo": "green_areas",
            "tipo": "LY",
        },
        {
            "nombre": "Infrastructure",
            "descripcion": "Infrastructure",
            "campo": "infrastructure",
            "tipo": "LY",
        },
        {
            "nombre": "Employment",
            "descripcion": "Employment",
            "campo": "jobs",
            "tipo": "LY",
        },
        {
            "nombre": "Permeable Area",
            "descripcion": "Permeable Area",
            "campo": "permeable_areas",
            "tipo": "LY",
        },
    ]
    default_indicadores = [
        {
            "nombre": "Superficie construida",
            "descripcion": "Superficie construida",
            "campo": "fp_area",
            "unidad": "km2",
        },
        {
            "nombre": "Población total",
            "descripcion": "Población total",
            "campo": "pop_2050",
            "unidad": "personas",
        },
        {
            "nombre": "Infraestructura vial expuesta a riesgos",
            "descripcion": "Infraestructura vial expuesta a riesgos",
            "campo": "pc_exposed_tr",
            "unidad": "%",
        },
        {
            "nombre": "Centros de salud expuesta a riesgos",
            "descripcion": "Centros de salud expuesta a riesgos",
            "campo": "pc_exposed_hp",
            "unidad": "%",
        },
        {
            "nombre": "Escuelas expuestas a riesgos",
            "descripcion": "Escuelas expuestas a riesgos",
            "campo": "pc_exposed_sc",
            "unidad": "%",
        },
        {
            "nombre": "Infraestructura electrica expuesta a riesgos",
            "descripcion": "Infraestructura electrica expuesta a riesgos",
            "campo": "pc_exposed_infra",
            "unidad": "%",
        },
        {
            "nombre": "Población expuesta a riesgos",
            "descripcion": "Población expuesta a riesgos",
            "campo": "pc_exposed_pop",
            "unidad": "%",
        },
        {
            "nombre": "Accesibilidad a hospitales",
            "descripcion": "Accesibilidad a hospitales",
            "campo": "pc_pop_hp",
            "unidad": "%",
        },
        {
            "nombre": "Accesibilidad a escuelas",
            "descripcion": "Accesibilidad a escuelas",
            "campo": "pc_pop_sc",
            "unidad": "%",
        },
        {
            "nombre": "Accesibilidad a espacios deportivos y recreativos",
            "descripcion": "Accesibilidad a espacios deportivos y recreativos",
            "campo": "pc_pop_sp",
            "unidad": "%",
        },
        {
            "nombre": "Accesibildad a clinicas",
            "descripcion": "Accesibildad a clinicas",
            "campo": "pc_pop_cl",
            "unidad": "%",
        },
        {
            "nombre": "Accesibilidad a guarderias",
            "descripcion": "Accesibilidad a guarderias",
            "campo": "pc_pop_dc",
            "unidad": "%",
        },
        {
            "nombre": "Accesibilidad a areas verdes",
            "descripcion": "Accesibilidad a areas verdes",
            "campo": "pc_pop_uga",
            "unidad": "%",
        },
        {
            "nombre": "Areas verdes per capita",
            "descripcion": "Areas verdes per capita",
            "campo": "uga_per_capita",
            "unidad": "m2/persona",
        },
        {
            "nombre": "Densidad de población",
            "descripcion": "Densidad de población",
            "campo": "pop_density",
            "unidad": "personas/km2",
        },
        {
            "nombre": "Expansion Urbana",
            "descripcion": "Expansion Urbana",
            "campo": "urban_expansion_area",
            "unidad": "km2",
        },
        {
            "nombre": "Densidad de empleo",
            "descripcion": "Densidad de empleo",
            "campo": "jobs_density",
            "unidad": "unidad económica/km2",
        },
        {
            "nombre": "Consumo de energía por alumbrado público",
            "descripcion": "Consumo de energía por alumbrado público",
            "campo": "public_lighting_energy_consumption",
            "unidad": "kWh/año",
        },
        {
            "nombre": "Consumo de suelo con cobertura vegetal",
            "descripcion": "Consumo de suelo con cobertura vegetal",
            "campo": "vg_area_loss",
            "unidad": "km2",
        },
        {
            "nombre": "Areas Permeables",
            "descripcion": "Areas Permeables",
            "campo": "permeable_area",
            "unidad": "km2",
        },
        {
            "nombre": "Consumo de energía residencial con medidas de eficiencia energética",
            "descripcion": "Consumo de energía residencial con medidas de eficiencia energética",
            "campo": "electricity_consumption_ee_per_capita",
            "unidad": "kWh/persona/año",
        },
        {
            "nombre": "Emisiones por transporte",
            "descripcion": "Emisiones por transporte",
            "campo": "transport_emissions_per_capita",
            "unidad": "kgCO2eq/persona/año",
        },
        {
            "nombre": "Generación de energía renovable con paneles solares",
            "descripcion": "Generación de energía renovable con paneles solares",
            "campo": "solar_energy_generation",
            "unidad": "kWh",
        },
        {
            "nombre": "Consumo de energía por edificación",
            "descripcion": "Consumo de energía por edificación",
            "campo": "electricity_consumption_buildings",
            "unidad": "kWh/persona/año",
        },
        {
            "nombre": "Costos de mantenimiento",
            "descripcion": "Costos de mantenimiento",
            "campo": "maintenance_cost",
            "unidad": "m.d.p.",
        },
        {
            "nombre": "Costos de inversion",
            "descripcion": "Costos de inversion",
            "campo": "capital_cost",
            "unidad": "m.d.p.",
        },
        {
            "nombre": "Tiempos de recorrido KVR",
            "descripcion": "Tiempos de recorrido KVR",
            "campo": "expected_vmt",
            "unidad": "km/año",
        },
        {
            "nombre": "Distribución modal (Bicicletas)",
            "descripcion": "Increase B",
            "campo": "increase_bicycle",
            "unidad": "%",
        },
        {
            "nombre": "Distribución modal (Privado)",
            "descripcion": "Increase W",
            "campo": "increase_private",
            "unidad": "%",
        },
        {
            "nombre": "Distribución modal (Transporte público)",
            "descripcion": "Increase TR",
            "campo": "increase_public_transport",
            "unidad": "%",
        },
        {
            "nombre": "Vivienda Media",
            "descripcion": "Vivienda Media",
            "campo": "pc_media_hu",
            "unidad": "%",
        },
        {
            "nombre": "Vivienda Popular",
            "descripcion": "Vivienda Popular",
            "campo": "pc_popular_hu",
            "unidad": "%",
        },
        {
            "nombre": "Vivienda Residencial",
            "descripcion": "Vivienda Residencial",
            "campo": "pc_residencial_hu",
            "unidad": "%",
        },
        {
            "nombre": "Consumo de agua per capita",
            "descripcion": "Consumo de agua per capita",
            "campo": "water_consumption",
            "unidad": "L/persona/dia",
        },
        {
            "nombre": "Consumo de energía por bombeo y tratamiento de agua",
            "descripcion": "Consumo de energía por bombeo y tratamiento de agua",
            "campo": "energy_consumption_water_supply",
            "unidad": "kWh/hogar/año",
        },
    ]
    default_escenarios = [
        {
            "structure": {"controles": {}},
            "nombre": "BAU Scenario",
            "descripcion": "The Business as Usual (BAU) scenario depicts how the city would perform in the future without interventions to promote climate-resilient cities. Under this scenario, cities would continue expanding, following the same patterns historically observed. Under the BAU scenario, investments in nature-based solutions, or new public transit lines are nonexistent, instead, financial resources are concentrated on basic urban infrastructure such as new roads and networks in the expansion areas and reconstruction in case of natural hazards.",
        },
        {
            "structure": {"controles": {}},
            "nombre": "Vision Scenario",
            "descripcion": "The Vision scenario shows the potential city performance in the future following ambitious low-carbon and climate-resilient urban interventions. Under the Vision Scenario, the assumptions might include energy efficiency and policies and climate-resilient solutions thus, policies and investments would aim for a significant reduction in emissions and reduced exposure to hazards.",
        },
        {
            "structure": {"controles": {}},
            "nombre": "My Scenario",
            "descripcion": "My Scenario allows the user to explore the potential impact of different policy combinations on achieving specific goals. This scenario is designed to be a user-friendly and interactive tool for exploring the potential consequences of various policy choices. It empowers the user to test, iterate, and gain insights into the complex landscape of policy interventions.",
        },
    ]
    for control in default_controles:
        _, _ = Control.objects.get_or_create(
            nombre=control["nombre"],
            descripcion=control["descripcion"],
            campo=control["campo"],
            tipo=control["tipo"],
            proyecto=project_instance,
            active=control.get("active", False)
        )
    for indicador in default_indicadores:
        _, _ = Indicador.objects.get_or_create(
            nombre=indicador["nombre"],
            descripcion=indicador["descripcion"],
            campo=indicador["campo"],
            unidad=indicador["unidad"],
            proyecto=project_instance,
        )
    for escenario in default_escenarios:
        _, _ = Escenario.objects.get_or_create(
            structure=escenario["structure"],
            nombre=escenario["nombre"],
            descripcion=escenario["descripcion"],
            proyecto=project_instance,
        )
