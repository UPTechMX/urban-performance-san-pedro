import csv
import json
import pandas as pd
from celery import chain
from rest_framework import viewsets
from urban_performance.projects.models import (
    Proyecto,
    Control,
    Indicador,
    Escenario,
    ProyectoStatus,
)
from urban_performance.up_geo.models import SpatialFile
from urban_performance.projects.serializers import (
    ProyectoSerializer,
    ControlSerializer,
    IndicadorSerializer,
    EscenarioSerializer,
    AssumptionsSerializer,
)
from urban_performance.projects.tasks import (
    process_project_controls,
    save_values,
    create_niveles,
)
from urban_performance.projects.utils import validate_assumptions_df
from urban_performance.up_geo.serializers import SpatialFileSerializer
from django.contrib import messages
from django.db import connections
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.generic import View
from rest_framework import status, response
from django.utils.translation import gettext_lazy as _


class ProyectoViewSet(viewsets.ModelViewSet):
    serializer_class = ProyectoSerializer

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            queryset = Proyecto.objects.filter(creado_por=self.request.user)
        else:
            queryset = Proyecto.objects.none()
        return queryset

    def update_assumptions(self, request, pk=None):
        proyecto = self.get_object()
        serializer = AssumptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            df = pd.DataFrame(serializer.validated_data["data"])
            is_valid = validate_assumptions_df(df=df, request=request)
        except Exception as e:
            messages.error(request, _("Please introduce a valid CSV file."))
            is_valid = False
        if is_valid:
            data = serializer.validated_data["data"]

            # We need to format the data for the csv writerows method
            row_list = [[""] + [x for x in data[0]]]
            pos = 1
            for element in data:
                row_list.append([f"{pos}"] + [x for x in element.values()])
                pos += 1

            # Write CSV data to file (replace with your CSV handling logic)
            with open(proyecto.assumptions.path, "w", newline="") as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerows(row_list)

            proyecto.estatus = ProyectoStatus.PROCESSING
            proyecto.save()
            chain(
                process_project_controls.s(proyecto_pk=proyecto.pk)
                | save_values.s(proyecto_pk=proyecto.pk)
                | create_niveles.s(proyecto_pk=proyecto.pk)
            )()
        return HttpResponse()

    def update(self, request, *args, **kwargs):
        spatial_files_counter: int = int(request.data.get("spatial_counter"))
        proyecto = self.get_object()
        request.data._mutable = True
        uso_como_template = request.data.get("uso_como_template", 0)
        request.data["uso_como_template"] = uso_como_template == "on"
        if request.FILES.get("assumptions"):
            request.data["assumptions"] = request.FILES["assumptions"]
        else:
            del request.data["assumptions"]
        serializer = self.get_serializer(proyecto, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            zip_file = request.FILES.get("spatial_zip_file")

            if zip_file:
                if zipfile.is_zipfile(zip_file):
                    extracted_files = {}
                    with zipfile.ZipFile(zip_file, "r") as z:
                        for file_info in z.infolist():
                            if not file_info.is_dir():  # Skip directories
                                extracted_files[file_info.filename] = z.read(
                                    file_info.filename
                                )
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
                    else:
                        try:
                            for (
                                category_code,
                                files_info,
                            ) in spatial_files_by_category.items():
                                for file_desc, file_content in files_info:
                                    file_name = f"{file_desc}"
                                    spatial_file = SpatialFile.objects.create(
                                        nombre=file_desc.split(".")[0].replace(
                                            "_", " "
                                        ),
                                        tipo=category_code,
                                        descripcion=file_desc.split(".")[0].replace(
                                            "_", " "
                                        ),
                                        proyecto=proyecto_instance,
                                        archivo=ContentFile(
                                            file_content, name=file_name
                                        ),
                                    )
                                    spatial_file.save()
                            SpatialFile.objects.filter(proyecto=proyecto).delete()
                        except Exception as e:
                            messages.error(
                                request,
                                f"Revisa los nombres de los archivos espaciales, por favor.",
                            )
                else:
                    messages.error(request, "A valid zip file must be uploaded.")
            if request.data.get("assumptions") or request.data.get("spatial_zip_file"):
                chain(
                    process_project_controls.s(proyecto_pk=proyecto.pk)
                    | save_values.s(proyecto_pk=proyecto.pk)
                    | create_niveles.s(proyecto_pk=proyecto.pk)
                )()

            messages.success(
                request,
                f"Project {proyecto.nombre} has been updated successfully.",
            )
        else:
            for error_message in serializer.custom_full_errors:
                messages.error(request, error_message)
        return HttpResponse()


class SpatialFileViewSet(viewsets.ModelViewSet):
    serializer_class = SpatialFileSerializer

    def get_queryset(self):
        proyecto_pk = self.kwargs.get("proyecto_pk")
        if proyecto_pk:
            return SpatialFile.objects.filter(proyecto__pk=proyecto_pk)
        else:
            return SpatialFile.objects.none()


class OpcionesView(viewsets.GenericViewSet):
    def get(self, *args, **kwargs):
        proyecto = Proyecto.objects.get(pk=kwargs["proyecto_pk"])
        df = pd.read_csv(proyecto.controles.path)
        response = {"opts": list(df.columns.values)}
        return JsonResponse(data=response, status=status.HTTP_200_OK)


class ControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.all()
    serializer_class = ControlSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by proyecto_pk if provided in the URL
        proyecto_pk = self.kwargs.get("proyecto_pk")
        if proyecto_pk:
            queryset = queryset.filter(proyecto__pk=proyecto_pk)
        return queryset


class IndicadorViewSet(viewsets.ModelViewSet):
    queryset = Indicador.objects.all()
    serializer_class = IndicadorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by proyecto_pk if provided in the URL
        proyecto_pk = self.kwargs.get("proyecto_pk")
        if proyecto_pk:
            queryset = queryset.filter(proyecto__pk=proyecto_pk)
        return queryset


class BaseEscenarioViewSet(viewsets.ModelViewSet):
    queryset = Escenario.objects.all()
    serializer_class = EscenarioSerializer

    def update(self, request, pk):
        escenario = self.get_object()
        serializer = self.serializer_class(
            escenario, data=request.data, partial=True
        )  # set partial=True to update a data partially
        if serializer.is_valid():
            serializer.save()
            return HttpResponse(status=201)
        return HttpResponse(status=400)


class EscenarioViewSet(BaseEscenarioViewSet):
    lookup_field = "proyecto"

    def create(self, request, *args, **kwargs):
        obj = Proyecto.objects.get(pk=self.kwargs["proyecto"])
        request.data.update({"proyecto": obj.pk})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class FilterUpControlsView(View):
    def post(self, request, *args, **kwargs):
        try:
            # Parse the JSON request body
            data = json.loads(request.body)

            # Start building the SQL query
            sql_query = f"SELECT * FROM urban_performance_controls WHERE project_id='{kwargs['proyecto_pk']}' AND "
            sql_conditions = []

            # Add each dictionary element as a filter (key='value')
            for key, value in data.items():
                sql_conditions.append(f"""{key} = { f"'{value}'" }""")

            # Combine the conditions with 'AND'
            sql_query += " AND ".join(sql_conditions)
            print(sql_query)

            # Execute the raw SQL query
            with connections["default"].cursor() as cursor:
                cursor.execute(sql_query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            # Convert the result to a list of dictionaries
            results = [dict(zip(columns, row)) for row in rows]

            # Return the results as a JSON response
            return JsonResponse({"results": results}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
