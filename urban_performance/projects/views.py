import os
import json
import pandas as pd
import shutil
import geopandas as gpd
import zipfile
from . import utils
from .tasks import process_project_controls, save_values, create_niveles
from .models import (
    Proyecto,
    create_defaults,
    ProyectoStatus,
    controls_path,
    assumptions_path,
    Control,
    Indicador,
    Escenario,
)
from celery import chain
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, reverse
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from urban_performance.up_geo.models import SpatialFile, spatial_path, SpatialOpts
from urban_performance.projects.serializers import ProyectoSerializer
from urban_performance.up_geo.serializers import SpatialFileSerializer
from django.contrib import messages
from django.db.models import Q

# Create your views here.


# TODO: Hacer esta vista compatible con ModelView, de momento sólo será
# template view.


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Proyecto

    def delete(self, *args, **kwargs):
        if not self.model.objects.filter(
            pk=self.kwargs["pk"], creado_por=self.request.user
        ).exists():
            messages.error(
                self.request,
                f"You're not allowed to do that.",
            )
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.success(
                self.request,
                f"Project has been deleted.",
            )
        return super().delete(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("projects:project_list")


class ProjectListView(ListView):
    model = Proyecto
    ordering = ["-creado_el"]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = self.model.objects.filter(
                Q(creado_por=self.request.user) | Q(visibilidad_publica=True)
            ).order_by(*self.ordering)
        else:
            queryset = self.model.objects.filter(visibilidad_publica=True).order_by(
                *self.ordering
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["proyectos_templates"] = self.model.objects.filter(
            uso_como_template=True
        )
        return context

    def post(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            request.POST._mutable = True
            from_template = request.POST.get("from-template")
            uso_como_template = request.POST.get("uso_como_template", 0)
            request.POST["uso_como_template"] = uso_como_template == "on"
            if from_template:
                try:
                    base_obj = Proyecto.objects.get(pk=from_template)
                    if base_obj.uso_como_template:
                        new_project = self.model.objects.create(
                            creado_por=self.request.user,
                            nombre=request.POST["nombre"],
                            descripcion=request.POST["descripcion"],
                            ciudad=request.POST["ciudad"],
                            uso_como_template=request.POST["uso_como_template"],
                            assumptions=base_obj.assumptions,
                            controles=base_obj.controles,
                        )
                        new_project_assumptions_path = assumptions_path(
                            new_project, None
                        )
                        os.makedirs(
                            os.path.dirname(
                                "urban_performance/media/"
                                + new_project_assumptions_path,
                            ),
                            exist_ok=True,
                        )
                        shutil.copy(
                            base_obj.assumptions.path,
                            "urban_performance/media/" + new_project_assumptions_path,
                        )
                        new_project.assumptions = new_project_assumptions_path

                        new_project_controls_path = controls_path(new_project, None)
                        os.makedirs(
                            os.path.dirname(
                                "urban_performance/media/" + new_project_controls_path
                            ),
                            exist_ok=True,
                        )
                        shutil.copy(
                            base_obj.controles.path,
                            "urban_performance/media/" + new_project_controls_path,
                        )
                        new_project.controles = new_project_controls_path

                        spatial_files = SpatialFile.objects.filter(proyecto=base_obj)
                        for spatial_file_base in spatial_files:
                            new_spatial_file = SpatialFile.objects.create(
                                nombre=spatial_file_base.nombre,
                                tipo=spatial_file_base.tipo,
                                descripcion=spatial_file_base.descripcion,
                                archivo=spatial_file_base.archivo,
                                proyecto=new_project,
                            )
                            filename = os.path.basename(spatial_file_base.archivo.path)
                            new_spatial_file_archivo_path = spatial_path(
                                new_spatial_file, filename
                            )
                            os.makedirs(
                                os.path.dirname(
                                    "urban_performance/media/"
                                    + new_spatial_file_archivo_path,
                                ),
                                exist_ok=True,
                            )
                            shutil.copy(
                                spatial_file_base.archivo.path,
                                "urban_performance/media/"
                                + new_spatial_file_archivo_path,
                            )
                            new_spatial_file.archivo = new_spatial_file_archivo_path
                            new_spatial_file.save()

                        escenarios = Escenario.objects.filter(proyecto=base_obj)
                        for escenario_base in escenarios:
                            new_escenario = Escenario.objects.create(
                                proyecto=new_project,
                                structure=escenario_base.structure,
                                nombre=escenario_base.nombre,
                                posicion=escenario_base.posicion,
                                descripcion=escenario_base.descripcion,
                            )

                        indicadores = Indicador.objects.filter(proyecto=base_obj)
                        for indicador_base in indicadores:
                            new_indicador = Indicador.objects.create(
                                proyecto=new_project,
                                nombre=indicador_base.nombre,
                                descripcion=indicador_base.descripcion,
                                campo=indicador_base.campo,
                                unidad=indicador_base.unidad,
                            )

                        controles = Control.objects.filter(proyecto=base_obj)
                        for control_base in controles:
                            new_control = Control.objects.create(
                                proyecto=new_project,
                                nombre=control_base.nombre,
                                descripcion=control_base.descripcion,
                                campo=control_base.campo,
                                tipo=control_base.tipo,
                            )

                        new_project.estatus = ProyectoStatus.READY
                        new_project.save()
                        messages.success(
                            request,
                            f"Proyect {new_project.ciudad} has been created from {base_obj.ciudad}.",
                        )
                    else:
                        messages.error(
                            request, "Proyect is not allowed to use as template."
                        )
                except ValidationError:
                    messages.error(request, "Proyect doesn't exist.")
            else:
                # New logic for handling the zip file
                zip_file = request.FILES.get("spatial_zip_file")

                if not zip_file or not zipfile.is_zipfile(zip_file):
                    messages.error(request, "A valid zip file must be uploaded.")
                    return redirect("projects:project_list")

                # Extract the zip file contents, including nested files
                extracted_files = {}
                with zipfile.ZipFile(zip_file, "r") as z:
                    for file_info in z.infolist():
                        if not file_info.is_dir():  # Skip directories
                            extracted_files[file_info.filename] = z.read(
                                file_info.filename
                            )

                # Categories that allow multiple files
                multiple_allowed_categories = {
                    "AP",
                    "AF",
                    "AT",
                    "ANB",
                    "AHO",
                    "ASC",
                    "ASP",
                    "ACL",
                    "ADC",
                    "AGA",
                    "AIN",
                    "AJO",
                    "APE",
                }

                # Initialize storage for spatial files
                spatial_files_by_category = {opt.value: [] for opt in SpatialOpts}

                # Process and categorize the extracted files
                for file_path, file_content in extracted_files.items():
                    if file_path.endswith(".geojson"):
                        file_name = os.path.basename(
                            file_path
                        )  # Get the file name, ignoring directories
                        parts = file_name.split("_", 2)
                        if len(parts) >= 2:
                            category_code, file_desc = parts[0], "_".join(parts[1:])
                            if category_code in spatial_files_by_category:
                                spatial_files_by_category[category_code].append(
                                    (file_desc, file_content)
                                )

                # Validate that all required categories have at least one file
                missing_categories = []
                for category_code, files in spatial_files_by_category.items():
                    if category_code in multiple_allowed_categories:
                        if len(files) < 1:
                            missing_categories.append(category_code)
                    else:
                        if len(files) != 1:
                            missing_categories.append(category_code)

                if missing_categories:
                    missing_categories_labels = [
                        str(SpatialOpts(category).label)
                        for category in missing_categories
                    ]
                    messages.error(
                        request,
                        f"Missing or incorrect number of files for categories: {', '.join(missing_categories_labels)}",
                    )
                    return redirect("projects:project_list")

                # Create the project
                request.POST["assumptions"] = request.FILES.get("assumptions")
                proyecto_serializer = ProyectoSerializer(
                    data=request.POST, context={"request": self.request}
                )

                if proyecto_serializer.is_valid():
                    try:
                        proyecto_instance = proyecto_serializer.save()
                    except IntegrityError as e:
                        messages.error(request, str(e))
                        return redirect("projects:project_list")

                    # Create SpatialFile instances from the validated files
                    for category_code, files_info in spatial_files_by_category.items():
                        for file_desc, file_content in files_info:
                            file_name = f"{file_desc}"
                            spatial_file = SpatialFile.objects.create(
                                nombre=file_desc.split(".")[0].replace("_", " "),
                                tipo=category_code,
                                descripcion=file_desc.split(".")[0].replace("_", " "),
                                proyecto=proyecto_instance,
                                archivo=ContentFile(file_content, name=file_name),
                            )
                            spatial_file.save()

                    # Process project controls asynchronously
                    create_defaults(project_instance=proyecto_instance)
                    chain(
                        process_project_controls.s(proyecto_instance.pk)
                        | save_values.s(proyecto_pk=proyecto_instance.pk)
                        | create_niveles.s(proyecto_pk=proyecto_instance.pk)
                    )()
                    messages.success(
                        request,
                        f"Project {proyecto_instance.nombre} has been created successfully.",
                    )
                else:
                    for error_message in proyecto_serializer.errors.values():
                        messages.error(request, error_message)
        else:
            messages.error(request, "Tienes que iniciar sesión para crear un proyecto.")
        return redirect("projects:project_list")


class ProjectDetailView(DetailView):
    # chart 1 - radar estándar
    # chart 2 - radar estándar, otro estilo
    # chart 3 - barras combinadas
    model = Proyecto
    categorias = [
        {
            "nombre": "Accesibilidad",
            "id": "ACC",
            "llaves": [],
            "chart": {
                "enabled": True,
                "tipo": "flor",
                "campos": [
                    "pc_pop_hp",
                    "pc_pop_sc",
                    "pc_pop_sp",
                    "pc_pop_cl",
                    "pc_pop_dc",
                    "pc_pop_uga",
                ],
            },
        },
        {
            "nombre": "Agua, energía y emisiones",
            "id": "ACC",
            "llaves": [
                "electricity_consumption_ee_per_capita",
                "transport_emissions_per_capita",
                "solar_energy_generation",
                "water_consumption",
                "energy_consumption_water_supply",
            ],
            "chart": {
                "enabled": False,
                "tipo": "flor",
                "campos": [],
            },
        },
        {
            "nombre": "Vivienda y empleo",
            "id": "VYE",
            "llaves": ["pop_2050", "density", "jobs_density"],
            "chart": {
                "enabled": True,
                "tipo": "barra",
                "campos": [
                    "pc_media_hu",
                    "pc_popular_hu",
                    "pc_residencial_hu",
                ],
            },
        },
        {
            "nombre": "Cambios de uso de suelo",
            "id": "CAM",
            "llaves": [
                "fp_area",
                "urban_exp_area",
                "vg_area_loss",
                "permeable_area",
                "ga_pc",
            ],
            "chart": {
                "enabled": False,
            },
        },
        {
            "nombre": "Peligros",
            "id": "PEL",
            "llaves": ["emissions_per_capita"],
            "chart": {
                "enabled": True,
                "tipo": "radar",
                "campos": [
                    "pc_exposed_tr",
                    "pc_exposed_hp",
                    "pc_exposed_sc",
                    "pc_exposed_infra",
                    "pc_exposed_pop",
                ],
            },
        },
        {
            "nombre": "Movilidad",
            "id": "MOV",
            "llaves": [
                "expected_vmt",
                "increase_bicycle",
                "increase_private",
                "increase_public_transport",
            ],
            "chart": {
                "enabled": False,
            },
        },
        {
            "nombre": "Costos",
            "id": "COS",
            "llaves": ["maintenance_cost", "capital_cost"],
            "chart": {
                "enabled": True,
                "tipo": "barra",
                "campos": ["maintenance_cost", "capital_cost"],
            },
        },
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj: Proyecto = self.get_object()
        if obj.estatus == ProyectoStatus.PROCESSING:
            messages.warning(
                self.request,
                f"Warning, project {obj.nombre} is currently being processed.",
            )
        elif obj.estatus == ProyectoStatus.ERROR:
            messages.error(
                self.request,
                f"Failed to process project {obj.nombre}. Please contact an administrator.",
            )
        df_controls = pd.DataFrame()
        assumptions_file = os.path.basename(obj.assumptions.file.name)
        df_assumptions = (
            pd.read_csv(
                f"./urban_performance/media/projects/{obj.uuid}/assumptions/{assumptions_file}"
            )
            .iloc[:, 1:]
            .fillna("")
        )
        context["assumptions"] = df_assumptions.to_dict(orient="records")
        context["controles"] = utils.get_controlls(obj, df_controls)
        context["indicadores"] = utils.get_indicators(obj, df_controls)
        context["escenarios"] = utils.get_scenarios(obj)
        context["base_map_elements"] = utils.get_base_map_elements(obj)
        context["obj_pk"] = obj.pk
        if self.request.user.is_authenticated:
            context["object_list"] = Proyecto.objects.filter(
                Q(visibilidad_publica=True) | Q(creado_por=self.request.user)
            )
        else:
            context["object_list"] = Proyecto.objects.filter(visibilidad_publica=True)
        context["categorias"] = self.categorias
        return context


def download_project_files(request, pk):
    proyecto = Proyecto.objects.get(pk=pk)
    carpeta_proyecto = proyecto.get_folder_path()
    filename = f"{carpeta_proyecto}{proyecto.ciudad}"
    shutil.make_archive(filename, "zip", carpeta_proyecto)

    return HttpResponse(
        open(f"{filename}.zip", "rb"),
        content_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}.zip",
            "Cache-Control": "no-cache",
        },
    )


def convert_geojson(request, path):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    geojson_path = f"{BASE_DIR}/{path}"
    gdf = gpd.read_file(geojson_path)

    if gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)

    geojson_converted = gdf.to_json()
    return JsonResponse(json.loads(geojson_converted), safe=False)
