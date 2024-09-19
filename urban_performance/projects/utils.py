import json
import os
import pandas as pd
from django.contrib import messages
from urban_performance.projects.models import Proyecto, Escenario
from urban_performance.up_geo.models import SpatialOpts
from django.db import connection

conversor = {
    "transit": SpatialOpts.ADDITIONAL_TRANSIT,
    "footprint": SpatialOpts.ADDITIONAL_FOOTPRINTS,
    "population_": SpatialOpts.ADDITIONAL_POPULATION,
    "nbs": SpatialOpts.ADDITIONAL_NBS,
    "hospitals": SpatialOpts.ADDITIONAL_HOSPITALS,
    "schools": SpatialOpts.ADDITIONAL_SCHOOLS,
    "sport_centers": SpatialOpts.ADDITIONAL_SPORTS,
    "clinics": SpatialOpts.ADDITIONAL_CLINICS,
    "daycare": SpatialOpts.ADDITIONAL_DAYCARE,
    "green_areas": SpatialOpts.ADDITIONAL_UGA,
    "infrastructure": SpatialOpts.ADDITIONAL_INFRA,
    "jobs": SpatialOpts.ADDITIONAL_JOBS,
    "permeable_areas": SpatialOpts.ADDITIONAL_PERMEABLE_AREAS,
}


def get_controlls(obj: Proyecto, df_controls: pd.DataFrame):
    controls_obj = {}
    ordering = "pk"
    controls = obj.control_set.all().order_by(ordering)
    spatial_files = obj.spatialfile_set.all()
    for control in controls:
        controls_obj[control.campo] = {
            "tipo": control.tipo,
            "nombre": control.nombre,
            "descripcion": control.descripcion,
            "active": control.active,
        }
        if control.tipo == "LY" or control.tipo == "SLY":
            layer_files = spatial_files.filter(tipo=conversor[control.campo])
            controls_obj[control.campo]["opciones"] = {}
            for x in layer_files:
                controls_obj[control.campo]["opciones"][
                    os.path.basename(x.archivo.name)
                ] = {"ruta": f"/media/{x.archivo.name}", "nombre": x.nombre}

        elif control.tipo == "RG":

            controls_obj[control.campo].update(
                {
                    "opciones": (
                        [0, 20, 40]
                        if control.campo == "energy_efficiency"
                        else [0, 5, 8.4] if control.campo == "solar_energy" else [0, 50]
                    ),
                }
            )
        elif control.tipo == "SW":
            controls_obj[control.campo].update(
                {
                    "nombre": control.nombre,
                }
            )
    return controls_obj


def get_max(prj_pk, campo):
    query = f"SELECT max({campo}) FROM urban_performance_controls WHERE project_id = '{str(prj_pk)}'"
    with connection.cursor() as cursor:
        cursor.execute(query)
        return float(cursor.fetchone()[0])


def get_min(prj_pk, campo):
    query = f"SELECT min({campo}) FROM urban_performance_controls WHERE project_id = '{str(prj_pk)}'"
    with connection.cursor() as cursor:
        cursor.execute(query)
        return float(cursor.fetchone()[0])


def get_indicators(obj: Proyecto, df_controls: pd.DataFrame):
    indicators_dict = {}
    ordering = "pk"
    for x in obj.indicador_set.all().order_by(ordering):
        indicators_dict.update(
            {
                x.campo: {
                    "campo": x.campo,
                    "unidad": x.unidad,
                    "nombre": x.nombre,
                    "niveles": json.loads(obj.niveles)[x.campo.lower()],
                    "descripcion": x.descripcion,
                }
            }
        )
    return indicators_dict


def get_controls_and_indicators(df_controls: pd.DataFrame):
    return df_controls.to_dict(orient="records")


def get_scenarios(obj: Proyecto):
    """
    Obtiene los escenarios asociados con un proyecto y crea nuevos si es necesario.

    Args:
        obj (Proyecto): Instancia del modelo Proyecto.

    Returns:
        QuerySet: Conjunto de escenarios asociados al proyecto.
    """

    escenarios = obj.escenario_set.all().order_by("posicion", "pk")[:3]

    # Si hay menos de 3 escenarios, crea nuevos hasta llegar a 3
    if escenarios.count() < 3:
        num_escenarios_creados = 3 - escenarios.count()
        for _ in range(num_escenarios_creados):
            Escenario.objects.create(
                proyecto=obj,
                nombre="Automatic Scenario",
                descripcion="Scenario created automatically",
                structure={"controles": {}},
            )
        escenarios = obj.escenario_set.all().order_by("posicion", "pk")
    escenarios_dict = {}
    for escenario in escenarios:
        escenarios_dict.update(
            {
                escenario.pk: {
                    "nombre": escenario.nombre,
                    "structure": escenario.structure,
                    "descripcion": escenario.descripcion,
                }
            }
        )
    return escenarios_dict


colores = {
    SpatialOpts.BASE_FOOTPRINT: "black",
    SpatialOpts.BASE_TRANSIT: "#1ddddd",
    SpatialOpts.HAZARD: "#ef5120",
    SpatialOpts.NBS: "#a1d318",
}


def get_base_map_elements(obj: Proyecto):
    ordering = "pk"
    base_spatial_files = obj.spatialfile_set.filter(
        tipo__in=[
            SpatialOpts.BASE_FOOTPRINT,
            SpatialOpts.BASE_TRANSIT,
            SpatialOpts.HAZARD,
            SpatialOpts.NBS,
        ]
    ).order_by(ordering)
    base_map_elements_dict = {}
    for sf in base_spatial_files:
        base_map_elements_dict.update(
            {
                sf.tipo: {
                    "nombre": sf.nombre,
                    "ruta": f"/media/{sf.archivo.name}",
                    "color": colores[sf.tipo],
                }
            }
        )
    return base_map_elements_dict


required_cols = [
    "expansion_cost_a",
    "nbs_c_cost",
    "transit_cost_a",
    "mantainance_expansion_cost_a",
    "nbs_m_cost",
    "mantainance_transit_cost_a",
    "recontruction_cost",
    "return_period",
    "elasticity_energy",
    "elasticity_emissions",
    "energy_consumption_base",
    "emissions_factor",
    "emissions_transport_percentage",
    "solar_panel_factor",
    "solar_energy",
    "mw_cost",
    "mw_capacity",
    "energy_buildings_percentage",
    "sc_c_cost",
    "hp_c_cost",
    "pk_c_cost",
    "sc_m_cost",
    "hp_m_cost",
    "pk_m_cost",
    "pv_incentive",
    "dc_c_cost",
    "dc_m_cost",
    "kvr",
    "vmt",
    "md_elasticity",
    "md_tr",
    "md_w",
    "md_b",
    "ga_c_cost",
    "ga_m_cost",
    "media_hu_water_cons",
    "popular_hu_water_cons",
    "residencial_hu_water_cons",
    "water_energy",
    "consumption_per_lamp",
    "cost_per_kW",
    "distance_between_lamps",
]


def validate_assumptions_df(df: pd.DataFrame, request=None):
    is_valid = True
    missing_cols = [col for col in required_cols if col not in df["code"].values]
    if missing_cols:
        if request:
            messages.error(
                request,
                f"The following fields are missing: {', '.join(missing_cols)}",
            )
        is_valid = False
    print(df)
    less_than_zero = df.loc[df["value"] < 0]
    if not less_than_zero.empty:
        if request:
            messages.error(
                request,
                "All values must be greather than zero.",
            )
        is_valid = False
    return is_valid
