import time
import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
from urban_performance.projects.utils import get_min, get_max


fiona.drvsupport.supported_drivers["KML"] = (
    "rw"  # Enable KML support for reading and writing
)

from datetime import datetime
from tqdm import tqdm
from typing import Any
import csv
from billiard import Pool

import os
from itertools import product, islice, chain
from uuid import uuid4
from celery import shared_task, group
from urban_performance.projects.models import (
    Proyecto,
    ProyectoStatus,
    Control,
    Indicador,
)
from urban_performance.up_geo.models import SpatialFile, SpatialOpts

from django.conf import settings
from django.db import connection

import json


def set_proyecto_progress(proyecto_pk: uuid4, progress: int):
    proyecto = Proyecto.objects.get(pk=proyecto_pk)
    proyecto.progress = progress
    proyecto.save()


@shared_task(soft_time_limit=300000)
def create_niveles(result: Any = None, proyecto_pk: str = ""):
    proyecto = Proyecto.objects.get(pk=proyecto_pk)
    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=90)
    indicadores = Indicador.objects.filter(proyecto=proyecto)
    niveles_dict = {}

    for indicador in indicadores:
        minimum: float = get_min(prj_pk=proyecto.pk, campo=indicador.campo)
        maximum: float = get_max(prj_pk=proyecto.pk, campo=indicador.campo)
        niveles_dict[indicador.campo.lower()] = {
            "menor": minimum,
            "mayor": maximum,
        }
    proyecto.niveles = json.dumps(niveles_dict)
    proyecto.estatus = ProyectoStatus.READY
    proyecto.save()
    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=100)


def read_filenames_from_path(path):
    """
    Reads all filenames ending with ".geojson" from a given path and
    saves them in a list with the specified name.

    Args:
        path: The directory path containing the GeoJSON files.

    Returns:
        A list containing the filenames from the specified path.
    """

    filenames = []

    # Loop through all files in the path
    for filename in os.listdir(path):
        if filename.endswith(".geojson"):
            # Extract and append the filename
            filenames.append(filename)

    return filenames


def make_serializable(value):
    if isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, tuple):
        return list(map(make_serializable, value))
    elif isinstance(value, dict):
        return {k: make_serializable(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [make_serializable(v) for v in value]
    else:
        return value


@shared_task(soft_time_limit=300000, time_limit=300001)
def process_project_controls(proyecto_pk: uuid4):
    proyecto = None
    while not proyecto:
        proyecto = Proyecto.objects.filter(pk=proyecto_pk)
        time.sleep(1)
    proyecto = proyecto[0]
    folder_path = proyecto.get_folder_path()
    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=0)

    # function
    def read_filenames_from_path(path):
        """
        Reads all filenames ending with ".geojson" from a given path and
        saves them in a list with the specified name.

        Args:
            path: The directory path containing the GeoJSON files.
            list_name: The name to assign to the list containing filenames.

        Returns:
            A list containing the filenames from the specified path.
        """

        filenames = []

        # Loop through all files in the path
        for filename in os.listdir(path):
            if filename.endswith(".geojson"):
                # Extract and append the filename
                filenames.append(filename)

        return filenames

    """## Starts the ***Urban Performance*** ⚡ calculations."""

    # Define working directory
    working_dir = folder_path

    # BASE ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬

    # Read BASE DATA (**CHANGE)
    pop_base = gpd.read_file(working_dir + "base/PB_poblacion_base.geojson")
    fp_base = gpd.read_file(working_dir + "base/BF_area_urbana_base.geojson")
    tr_base = gpd.read_file(working_dir + "base/BT_lineas_transporte_base.geojson")
    green_area = gpd.read_file(working_dir + "base/GA_areas_verdes_base.geojson")
    sports = gpd.read_file(working_dir + "base/SP_centros_deportivos_base.geojson")
    hospitals = gpd.read_file(working_dir + "base/HO_hospitales_base.geojson")
    schools = gpd.read_file(working_dir + "base/SC_escuelas_base.geojson")
    clinics = gpd.read_file(working_dir + "base/CL_centro_salud_base.geojson")
    daycare = gpd.read_file(working_dir + "base/DC_guarderia_base.geojson")
    veg_cover_base = gpd.read_file(working_dir + "base/VB_cobertura_vegetal.geojson")
    roads_base = gpd.read_file(
        working_dir + "base/RB_roads_base.geojson"
    )  ##NUEVO AGREGAR
    hazard = gpd.read_file(working_dir + "hazard/HZ_inundaciones_disuelta.geojson")

    # Projected crs
    pop_base_projected = pop_base.to_crs("World_Mollweide")
    fp_base_projected = fp_base.to_crs("World_Mollweide")
    tr_base_projected = tr_base.to_crs("World_Mollweide")
    green_area_projected = green_area.to_crs("World_Mollweide")
    sports_base_projected = sports.to_crs("World_Mollweide")
    hospitals_base_projected = hospitals.to_crs("World_Mollweide")
    schools_base_projected = schools.to_crs("World_Mollweide")
    clinics_base_projected = clinics.to_crs("World_Mollweide")
    daycare_base_projected = daycare.to_crs("World_Mollweide")
    veg_cover_base_projected = veg_cover_base.to_crs("World_Mollweide")
    roads_base_projected = roads_base.to_crs("World_Mollweide")
    exposure_polygon_projected = hazard.to_crs("World_Mollweide")

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=20)

    # BASE CALCULATIONS |||||||||||||||||||||||||||||||||||||

    # POPULATION
    # Calculate the total population
    pop_base = round(pop_base["Pop_total"].sum(), 0)  # population base

    # FOOTPRINT
    # Calculate the area of footprint in square kilometers
    fp_base_area = fp_base_projected.area.sum() / 1e6  # footprint base area
    density_base = pop_base / fp_base_area  # population density base

    # TRANSIT
    tr_base_buffer = tr_base_projected.buffer(400)
    tr_base_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(tr_base_buffer))

    # GREEN AREA
    ga_base_area = green_area_projected.area.sum() / 1e6

    # AMENITIES ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
    # Hospitals
    hospitals_base_buffer = hospitals_base_projected.buffer(500)
    hospitals_base_buffer = gpd.GeoDataFrame(
        geometry=gpd.GeoSeries(hospitals_base_buffer)
    )
    # Hospitals area & number of hospitals in the base layer
    hospitals_base_area = hospitals_base_buffer.area.sum() / 1e6
    hospitals_count_base = len(hospitals_base_projected)

    # Schools
    schools_base_buffer = schools_base_projected.buffer(500)
    schools_base_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(schools_base_buffer))
    # Schools buffer area & number of schools in the base layer
    schools_base_area = schools_base_buffer.area.sum() / 1e6
    schools_count_base = len(schools_base_projected)

    # Clinics
    clinics_base_buffer = clinics_base_projected.buffer(500)
    clinics_base_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(clinics_base_buffer))
    # Clinics buffer area & number of clinics in the base layer
    clinics_base_area = clinics_base_buffer.area.sum() / 1e6
    clinics_count_base = len(clinics_base_projected)

    # Sport centers
    sports_base_buffer = sports_base_projected.buffer(500)
    sports_base_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(sports_base_buffer))
    sports_base_area = sports_base_buffer.area.sum() / 1e6
    sports_count_base = len(sports_base_projected)

    # Daycare
    daycare_base_buffer = daycare_base_projected.buffer(500)
    daycare_base_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(daycare_base_buffer))
    # Daycare buffer area & number of daycare centers in the base layer
    daycare_base_area = daycare_base_buffer.area.sum() / 1e6
    daycare_count_base = len(daycare_base_projected)

    # ROADS
    roads_fp_base = gpd.overlay(
        roads_base_projected, fp_base_projected, how="intersection"
    )
    roads_length_base = roads_fp_base.length.sum() / 1e3
    roads_dens_base = roads_length_base / fp_base_area  # roads density base

    # ASSUMPTIONS  |||||||||||||||||||||||||||||||||||||||||
    # Read CSV file as a pandas DataFrame
    assumptions_dir = working_dir + "/assumptions"
    assumptions = pd.read_csv(assumptions_dir + "/assumptions_SP.csv")
    # Convert values to int
    assumptions = dict(zip(assumptions["code"], assumptions["value"]))

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=7.5)

    # Define working directory
    working_dir = folder_path

    working_folders = [
        "population/",
        "footprints/",
        "transit/",
        "nbs/",
        "hospitals/",
        "schools/",
        "sports/",
        "clinics/",
        "daycare/",
        "green areas/",
        "infraestructure/",
        "employment/",
        "permeable areas/",
    ]

    energy_efficieny = [
        0,
        20,
        40,
    ]  # Represents the percentage of energy saving i.e 0% 40% 15%
    solar_energy = [
        0,
        8.4,
        5,
    ]  # Percentage of the footprint where panels will be installed
    RWH = [0, 50]  # Percentage of the water supply with rain water harvesting

    # Add main path to subpaths
    path = [working_dir + folder for folder in working_folders]

    # Read filenames into respective lists using the function
    population = read_filenames_from_path(path[0])
    footprint = read_filenames_from_path(path[1])
    transit = read_filenames_from_path(path[2])
    nbs = read_filenames_from_path(path[3])
    hospitals = read_filenames_from_path(path[4])
    schools = read_filenames_from_path(path[5])
    sports = read_filenames_from_path(path[6])
    clinics = read_filenames_from_path(path[7])
    daycare = read_filenames_from_path(path[8])
    UGA = read_filenames_from_path(path[9])
    infra = read_filenames_from_path(path[10])
    jobs = read_filenames_from_path(path[11])
    perm = read_filenames_from_path(path[12])

    # Use itertools.product to generate all combinations
    # scenarios = [*product(population, footprint, transit, nbs, energy_efficieny, solar_energy, RWH, hospitals, schools, sports, clinics, daycare, UGA, infra, jobs, perm)]

    """# Partial results (URBAN PERFORMANCE)"""
    progress = 20

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=progress)

    # Partial results POPULATION ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
    partial_pop = {}

    for filename in population:
        progress += 10
        # Read file & reproject geojson
        pop = gpd.read_file(path[0] + filename)
        pop_projected = pop.to_crs("World_Mollweide")
        # Get population
        pop_2050 = round(pop["Pop_total"].sum(), 0)  # future population

        # Calculate density
        pop_projected["Shape_Area"] = pop_projected.area / 1e4
        pop_projected["DENS2050"] = (
            pop_projected["Pop_total"] / pop_projected["Shape_Area"]
        )

        # Intersect population with hazards
        inter = gpd.overlay(
            pop_projected, exposure_polygon_projected, how="intersection"
        )

        # HAZARDS/NBS ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
        partial_nbs = {}
        # NBS
        for nbs_filename in nbs:
            # Read file & reproject geojson
            nbs_gdf = gpd.read_file(path[3] + nbs_filename)
            nbs_projected = nbs_gdf.to_crs("World_Mollweide")

            # Intersect population base with nbs_projected
            inter_NBS = gpd.overlay(
                pop_base_projected, nbs_projected, how="intersection"
            )
            inter_exp = gpd.overlay(
                inter, inter_NBS, how="difference", keep_geom_type=False
            )  # Remove nbs

            # NBS_TRANSIT
            partial_nbs_tr = {}
            for tr_filename in transit:
                tr = gpd.read_file(path[2] + tr_filename)
                tr_projected = tr.to_crs("World_Mollweide")
                # Create a buffer
                tr_buffer = tr_projected.buffer(10)  # change buffer i.e. 10m
                tr_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(tr_buffer))
                tr_buffer_area = tr_buffer.area.sum() / 1e6
                # Transit lines exposed to hazards
                exposed_tr = gpd.overlay(tr_buffer, inter_exp, how="intersection")
                # Count the number of intersecting points
                count_tr_exposed = exposed_tr.area.sum() / 1e6
                pc_exposed_tr = (count_tr_exposed * 100) / tr_buffer_area
                partial_nbs_tr[tr_filename] = (
                    pc_exposed_tr  # percentage of transit lines exposed to hazards
                )

            # NBS_HOSPITALS
            partial_nbs_hp = {}
            for hp_filename in hospitals:
                hp = gpd.read_file(path[4] + hp_filename)
                hp_projected = hp.to_crs("World_Mollweide")
                total_hp = len(hp_projected)
                # exposed
                exposed_hp = gpd.sjoin(
                    hp_projected, inter_exp, how="inner", predicate="intersects"
                )
                # Count the number of intersecting points
                count_hp_exposed = len(exposed_hp)
                pc_exposed_hp = (count_hp_exposed * 100) / total_hp
                partial_nbs_hp[hp_filename] = (
                    pc_exposed_hp  # percentage of hospitals exposed to hazards
                )

            # NBS_SCHOOLS
            partial_nbs_sc = {}
            for sc_filename in schools:
                sc = gpd.read_file(path[5] + sc_filename)
                sc_projected = sc.to_crs("World_Mollweide")
                total_sc = len(sc_projected)
                # exposed
                exposed_sc = gpd.sjoin(
                    sc_projected, inter_exp, how="inner", predicate="intersects"
                )
                # Count the number of intersecting points
                count_sc_exposed = len(exposed_sc)
                pc_exposed_sc = (count_sc_exposed * 100) / total_sc
                partial_nbs_sc[sc_filename] = (
                    pc_exposed_sc  # percentage of schools exposed to hazards
                )

            # INFRASTRUCTURE
            partial_nbs_infra = {}
            for infra_filename in infra:
                infra_gpd = gpd.read_file(path[10] + infra_filename)
                infra_projected = infra_gpd.to_crs("World_Mollweide")
                # Create a buffer
                infra_buffer = infra_projected.buffer(10)  # change buffer i.e. 10m
                infra_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(infra_buffer))
                infra_buffer_area = infra_buffer.area.sum() / 1e6
                # Infraestructure lines exposed to hazards
                exposed_infra = gpd.overlay(infra_buffer, inter_exp, how="intersection")
                # Count the number of intersecting points
                count_infra_exposed = exposed_infra.area.sum() / 1e6
                pc_exposed_infra = (count_infra_exposed * 100) / infra_buffer_area
                partial_nbs_infra[infra_filename] = (
                    pc_exposed_infra  # percentage of infrastructure exposed to hazards
                )

            # Calculate area
            inter["Shape_Area"] = inter.area / 1e4  # NEW
            exposed_area = inter["Shape_Area"].sum()
            inter["Pop_total"] = inter["DENS2050"] * inter["Shape_Area"]  # NEW
            exposed_pop = round(
                inter["Pop_total"].sum(), 0
            )  # total population exposed to hazards
            pc_exposed_pop = (
                inter["Pop_total"].sum() * 100 / pop_2050
            )  # NEW #percentage of population exposed to hazards
            if pc_exposed_pop > 100:
                pc_exposed_pop = 100

            # __ASSUMPTIONS__
            # Capital cost NBS
            nbs_cost = assumptions["nbs_c_cost"]
            # Maintenance cost NBS
            nbs_maintenance = assumptions["nbs_m_cost"]

            # Calculate area
            nbs_area = nbs_projected.area.sum() / 1e6
            nbs_c_cost = nbs_area * nbs_cost  # natural base solution capital cost
            nbs_m_cost = (
                nbs_area * nbs_maintenance
            )  # natural base solution maintenance cost

            # Calculate maintenance costs for flooding risk
            exposure_factor = assumptions["recontruction_cost"]
            return_period = assumptions["return_period"]
            reconstruction_cost = (exposed_pop * exposure_factor) / return_period
            # Save partial nbs values
            partial_nbs[nbs_filename] = (
                exposed_area,
                exposed_pop,
                partial_nbs_tr,
                partial_nbs_hp,
                partial_nbs_sc,
                partial_nbs_infra,
                pc_exposed_pop,
                nbs_c_cost,
                nbs_m_cost,
                reconstruction_cost,
            )

        # AMENITIES ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬

        # HOSPITALS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_hp = {}
        # schools exposed to hazards
        for hp_filename in hospitals:
            hp = gpd.read_file(path[4] + hp_filename)
            hp_projected = hp.to_crs("World_Mollweide")
            # Create a buffer
            hp_buffer = hp_projected.buffer(800)
            hp_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(hp_buffer))
            hp_buffer_dissolved = hp_buffer.dissolve()

            # Intersection
            hp_intersection = gpd.overlay(
                pop_projected, hp_buffer_dissolved, how="intersection"
            )
            # Calculate area
            hp_intersection["Shape_Area"] = hp_intersection.area / 1e4  # NEW
            hp_intersection["Pop_total"] = (
                hp_intersection["DENS2050"] * hp_intersection["Shape_Area"]
            )  # NEW
            pc_pop_near_hp = (
                hp_intersection["Pop_total"].sum() * 100 / pop_2050
            )  # NEW #percentage of population near a hospital
            if pc_pop_near_hp > 100:
                pc_pop_near_hp = 100
            partial_hp[hp_filename] = pc_pop_near_hp

        # SCHOOLS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_sc = {}
        # schools exposed to hazards
        for sc_filename in schools:
            sc = gpd.read_file(path[5] + sc_filename)
            sc_projected = sc.to_crs("World_Mollweide")
            # Create a buffer
            sc_buffer = sc_projected.buffer(800)
            sc_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(sc_buffer))
            sc_buffer_dissolved = sc_buffer.dissolve()

            # intersection
            sc_intersection = gpd.overlay(
                pop_projected, sc_buffer_dissolved, how="intersection"
            )
            # Calculate area
            sc_intersection["Shape_Area"] = sc_intersection.area / 1e4  # NEW
            sc_intersection["Pop_total"] = (
                sc_intersection["DENS2050"] * sc_intersection["Shape_Area"]
            )  # NEW
            pc_pop_near_sc = (
                sc_intersection["Pop_total"].sum() * 100 / pop_2050
            )  # NEW #percentage of population near a school
            if pc_pop_near_sc > 100:
                pc_pop_near_sc = 100
            partial_sc[sc_filename] = pc_pop_near_sc

        # SPORTS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_sp = {}
        for sp_filename in sports:
            sp = gpd.read_file(path[6] + sp_filename)
            sp_projected = sp.to_crs("World_Mollweide")
            # Create a buffer
            sp_buffer = sp_projected.buffer(800)
            sp_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(sp_buffer))
            # Intersection
            sp_buffer_dissolved = sp_buffer.dissolve()
            sp_intersection = gpd.overlay(
                pop_projected, sp_buffer_dissolved, how="intersection"
            )
            # pk_intersection.plot()
            sp_intersection["Shape_Area"] = sp_intersection.area / 1e4  # NEW
            sp_intersection["Pop_total"] = (
                sp_intersection["DENS2050"] * sp_intersection["Shape_Area"]
            )  # NEW
            pc_pop_near_sp = (
                sp_intersection["Pop_total"].sum() * 100 / pop_2050
            )  # NEW #percentage of population near a sport center
            if pc_pop_near_sp > 100:
                pc_pop_near_sp = 100
            partial_sp[sp_filename] = pc_pop_near_sp

        # CLINICS ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_cl = {}
        for cl_filename in clinics:
            cl = gpd.read_file(path[7] + cl_filename)
            cl_projected = cl.to_crs("World_Mollweide")
            # Create a buffer
            cl_buffer = cl_projected.buffer(800)
            cl_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(cl_buffer))
            # Intersection
            cl_buffer_dissolved = cl_buffer.dissolve()
            cl_intersection = gpd.overlay(
                pop_projected, cl_buffer_dissolved, how="intersection"
            )

            cl_intersection["Shape_Area"] = cl_intersection.area / 1e4  # NEW
            cl_intersection["Pop_total"] = (
                cl_intersection["DENS2050"] * cl_intersection["Shape_Area"]
            )  # NEW
            pc_pop_near_cl = (
                cl_intersection["Pop_total"].sum() * 100 / pop_2050
            )  # NEW percentage of population near a health clinic
            if pc_pop_near_cl > 100:
                pc_pop_near_cl = 100
            partial_cl[cl_filename] = pc_pop_near_cl

        # DAYCARE ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_dc = {}
        for dc_filename in daycare:
            dc = gpd.read_file(path[8] + dc_filename)
            dc_projected = dc.to_crs("World_Mollweide")
            # Create a buffer
            dc_buffer = dc_projected.buffer(800)
            dc_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(dc_buffer))
            # Intersection
            dc_buffer_dissolved = dc_buffer.dissolve()
            dc_intersection = gpd.overlay(
                pop_projected, dc_buffer_dissolved, how="intersection"
            )

            dc_intersection["Shape_Area"] = dc_intersection.area / 1e4  # NEW
            dc_intersection["Pop_total"] = (
                dc_intersection["DENS2050"] * dc_intersection["Shape_Area"]
            )  # NEW
            pc_pop_near_dc = dc_intersection["Pop_total"].sum() * 100 / pop_2050  # NEW
            if pc_pop_near_dc > 100:
                pc_pop_near_dc = 100
            partial_dc[dc_filename] = pc_pop_near_dc

        # UGA |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_UGA = {}
        for uga_filename in UGA:
            # UGA
            uga = gpd.read_file(path[9] + uga_filename)
            uga_projected = uga.to_crs("World_Mollweide")
            # Create a buffer
            uga_buffer = uga_projected.buffer(800)
            uga_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(uga_buffer))
            uga_buffer_dissolved = uga_buffer.dissolve()
            # uga_buffer_dissolved = uga_projected #CHANGE

            # green areas exposed to hazards
            uga_area = uga_projected.area.sum() / 1e6
            uga_per_capita = (uga_area / pop_2050) * 1e6  # green area per capita
            # Intersection
            uga_intersection = gpd.overlay(
                pop_projected, uga_buffer_dissolved, how="intersection"
            )
            # Calculate area
            uga_intersection["Shape_Area"] = uga_intersection.area / 1e4  # NEW
            uga_intersection["Pop_total"] = (
                uga_intersection["DENS2050"] * uga_intersection["Shape_Area"]
            )  # NEW
            pc_pop_near_uga = (
                uga_intersection["Pop_total"].sum() * 100 / pop_2050
            )  # NEW # percentage of population near a green area
            if pc_pop_near_uga > 100:
                pc_pop_near_uga = 100

            # __ASSUMPTIONS__
            # Capital cost ga
            ga_cost = assumptions["ga_c_cost"]
            # Maintenance cost ga
            ga_maintenance = assumptions["ga_m_cost"]
            # Calculate costs
            ga_c_cost = uga_area * ga_cost * 1e6
            ga_m_cost = uga_area * ga_maintenance * 1e6
            partial_UGA[uga_filename] = (
                uga_area,
                uga_per_capita,
                pc_pop_near_uga,
                ga_c_cost,
                ga_m_cost,
            )

        # HOUSING TYPOLOGIES |||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        housing_types = pop.melt(
            id_vars=["CVEGEO"],  # Columns to keep as identifiers
            value_vars=[
                "Residencial_hu",
                "Media_hu",
                "Popular_hu",
            ],  # Columns to unpivot
            var_name="Housing_Type",  # Name for the new column containing the original column names
            value_name="Value",  # Name for the new column containing the corresponding values
        )
        housing_types = housing_types.groupby(["Housing_Type"])["Value"].sum()
        housing_types_pct = housing_types / housing_types.sum() * 100
        # partial_ht
        partial_ht = housing_types_pct.to_dict()  # Proportion of housing types
        housing_types = housing_types.to_frame(name="Total")

        # partial_ht_RWH
        # Assumptions
        Media_hu_water_cons = assumptions["media_hu_water_cons"]
        Popular_hu_water_cons = assumptions["popular_hu_water_cons"]
        Residencial_hu_water_cons = assumptions["residencial_hu_water_cons"]
        water_energy = assumptions["water_energy"]

        # Column with assumptions
        housing_types["water_assumption"] = [
            Media_hu_water_cons,
            Popular_hu_water_cons,
            Residencial_hu_water_cons,
        ]
        # Get total water consumption
        housing_types["water_consumption"] = (
            housing_types["Total"] * housing_types["water_assumption"]
        )

        partial_ht_RWH = {}
        for perc_RWH in RWH:
            # Water supply with RWH
            housing_types["RWH"] = housing_types["water_consumption"] * (perc_RWH / 100)
            # Other sources
            housing_types["other_sources"] = (
                housing_types["water_consumption"] - housing_types["RWH"]
            )
            # Energy required to supply the complement
            housing_types["energy_water_supply"] = (
                housing_types["other_sources"] * water_energy
            )
            water_consumption = (
                housing_types["water_consumption"].sum() * 4 * 1000 / (pop_2050 * 365)
            )
            energy_consumption_water_supply = housing_types["energy_water_supply"].sum()
            partial_ht_RWH[perc_RWH] = (
                water_consumption,
                energy_consumption_water_supply,
            )

        partial_ht.update(partial_ht_RWH)
        # __RESULTS__
        # Partial results saved in a dictionary
        partial_pop[filename] = (
            pop_2050,
            partial_nbs,
            partial_hp,
            partial_sc,
            partial_sp,
            partial_cl,
            partial_dc,
            partial_UGA,
            partial_ht,
        )

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=71)
    print(partial_pop)

    # Partial results FOOTPRINT ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
    partial_fp = {}

    for filename in footprint:
        # Read file
        fp = gpd.read_file(path[1] + filename)
        # Projected
        fp_projected = fp.to_crs("World_Mollweide")
        # Footprint area
        fp_area = fp_projected.area.sum() / 1e6

        # HOSPITALS ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_hp = {}
        # hospitals exposed to hazards
        for hp_filename in hospitals:
            hp = gpd.read_file(path[4] + hp_filename)
            hp_projected = hp.to_crs("World_Mollweide")
            # Count the total of hospitals
            total_hp = len(hp_projected)

            # __ASUMPTIONS__
            # Capital cost new health clinics
            hp_cost = assumptions["hp_c_cost"]
            # Maintenance cost hospitals
            hp_maintenance = assumptions["hp_m_cost"]

            # Get the number of new hospitals
            new_hp = total_hp - hospitals_count_base
            # Total cost for new hospitals
            hospital_c_cost = new_hp * hp_cost
            # Maintenance cost for hospitals
            hospital_m_cost = total_hp * hp_maintenance
            # Save calculated values
            partial_hp[hp_filename] = (
                total_hp,
                hospital_c_cost,
                hospital_m_cost,
                new_hp,
            )

        # SCHOOLS ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_sc = {}
        # schools exposed to hazards
        for sc_filename in schools:
            sc = gpd.read_file(path[5] + sc_filename)
            sc_projected = sc.to_crs("World_Mollweide")
            # Count the total of schools
            total_sc = len(sc_projected)

            ##__ASUMPTIONS__
            # Capital cost new schools
            school_cost = assumptions["sc_c_cost"]
            # Maintenance cost schools
            school_maintenance = assumptions["sc_m_cost"]

            # Get the number of new schools
            new_sc = total_sc - schools_count_base
            # Total cost for new schools
            school_c_cost = new_sc * school_cost
            # Maintenance cost schools
            school_m_cost = total_sc * school_maintenance
            # Save calculated values
            partial_sc[sc_filename] = (total_sc, school_c_cost, school_m_cost, new_sc)

        # SPORT CENTERS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_sp = {}
        for sp_filename in sports:
            sp = gpd.read_file(path[6] + sp_filename)
            sp_projected = sp.to_crs("World_Mollweide")
            # Count the total of sport centers
            total_sp = len(sp_projected)

            # __ASUMPTIONS__
            # Capital cost new parks
            sp_cost = assumptions["pk_c_cost"]
            # Maintenance cost parks
            sp_maintenance = assumptions["pk_m_cost"]

            # Get the number of new parks/sport centers
            new_sp = total_sp - sports_count_base
            # Total cost for new parks/sport centers
            sport_c_cost = new_sp * sp_cost
            # Maintenance cost parks
            sport_m_cost = total_sp * sp_maintenance
            # Save calculated values
            partial_sp[sp_filename] = (total_sp, sport_c_cost, sport_m_cost, new_sp)

        # CLINICS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_cl = {}
        # hospitals exposed to hazards
        for cl_filename in clinics:
            cl = gpd.read_file(path[7] + cl_filename)
            cl_projected = cl.to_crs("World_Mollweide")
            # Count the total of hospitals
            total_cl = len(cl_projected)

            # __ASUMPTIONS__
            # Capital cost new health clinics
            cl_cost = assumptions["hp_c_cost"]  # CAMBIAR clinics
            # Maintenance cost health clinics
            cl_maintenance = assumptions["hp_m_cost"]

            # Get the number of new clinics
            new_cl = total_cl - clinics_count_base
            # Total cost for new clinics
            clinic_c_cost = new_cl * cl_cost
            # Maintenance cost health clinics
            clinic_m_cost = total_cl * cl_maintenance
            # Save calculated values
            partial_cl[cl_filename] = (total_cl, clinic_c_cost, clinic_m_cost, new_cl)

        # DAYCARE |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_dc = {}
        for dc_filename in daycare:
            dc = gpd.read_file(path[8] + dc_filename)
            dc_projected = dc.to_crs("World_Mollweide")
            # daycare
            # fp_dc = gpd.sjoin(dc_projected, fp_projected, how='inner', predicate='intersects')
            # total_dc = len(fp_dc)
            total_dc = len(dc_projected)

            # Capital cost new daycare center
            dc_cost = assumptions["dc_c_cost"]
            # Maintenance cost daycare
            dc_maintenance = assumptions["dc_m_cost"]
            # new daycare
            new_dc = total_dc - daycare_count_base
            dc_c_cost = new_dc * dc_cost
            # Maintenance cost daycare
            dc_m_cost = total_dc * dc_maintenance
            partial_dc[dc_filename] = (total_dc, dc_c_cost, dc_m_cost, new_dc)

        # URBAN EXPANSION |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        urban_exp_poly = gpd.overlay(fp_projected, fp_base_projected, how="difference")
        urban_expansion_area = urban_exp_poly.area.sum() / 1e6  # Urban expansion area

        # JOBS DENSITY ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_jobs = {}
        for jobs_filename in jobs:
            jobs_gpd = gpd.read_file(path[11] + jobs_filename)
            jobs_projected = jobs_gpd.to_crs("World_Mollweide")
            # Jobs density
            fp_jobs = gpd.sjoin(
                jobs_projected, fp_projected, how="inner", predicate="intersects"
            )
            total_jobs = len(fp_jobs)
            jobs_density = total_jobs / fp_area
            partial_jobs[jobs_filename] = jobs_density

        # VEGETAL COVER LOSS ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        vg_area_base = veg_cover_base_projected.area.sum() / 1e6
        vg_loss = gpd.overlay(veg_cover_base_projected, fp_projected, how="difference")
        vg_area_remain = vg_loss.area.sum() / 1e6
        vg_area_loss = vg_area_base - vg_area_remain

        # SOLAR ENERGY ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        partial_solar = {}
        for solar_energy_percentage in solar_energy:

            # __ASSUMPTIONS__
            solar_energy_val = assumptions["solar_energy"]
            solar_panel_factor = assumptions["solar_panel_factor"]

            fp_solar_area = (fp_area * (solar_energy_percentage / 100)) * 1000000
            # Installed capacity
            installed_capacity = solar_panel_factor * fp_solar_area
            # Calculate the potential solar energy generation
            solar_energy_generation = installed_capacity * solar_energy_val  # kWh/year
            # potential_solar_energy_generation_PC=potential_solar_energy_generation/pop_2050 # REMAIN

            # __ASSUMPTIONS__
            mw_cost = assumptions["mw_cost"]
            pv_incentive = assumptions["pv_incentive"]
            mw_capacity = assumptions["mw_capacity"]

            sol_gen_GWh = solar_energy_generation / 1000000
            energy_capacity = sol_gen_GWh / (mw_capacity * 1000)
            capital_solar_1 = mw_cost * energy_capacity
            # Total capital cost for solar energy
            capital_solar = (pv_incentive / 100) * capital_solar_1
            # Save calculated values
            partial_solar[solar_energy_percentage] = (
                solar_energy_generation,
                capital_solar_1,
                capital_solar,
            )

        # ROADS DENSITY |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        # density
        roads_fp = gpd.overlay(roads_base_projected, fp_projected, how="intersection")
        roads_length = roads_fp.length.sum() / 1e3
        # roads_density = (roads_length/fp_area)

        # ENERGY CONSUMPTION |||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        # public lightning
        consumption_per_lamp = assumptions["consumption_per_lamp"]
        cost_per_kW = assumptions["cost_per_kW"]
        distance_between_lamps = assumptions["distance_between_lamps"]

        # Calculate the consumption associated to public lightning
        public_lighting_energy_consumption = (
            roads_length / distance_between_lamps * consumption_per_lamp
        )  # total consumption for public lightning
        cost_public_lighting = (
            public_lighting_energy_consumption * cost_per_kW
        )  # total cost for public lightning

        # MAINTENANCE COSTS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        # footprint costs
        maintenance_factor_fp = assumptions["mantainance_expansion_cost_a"]
        maintenance_fp = fp_area * maintenance_factor_fp
        # maintenance_urban_footprint
        maintenance_fp = (maintenance_fp * (2050 - 2025)) / 1e6  # Could this change?

        # CAPITAL COSTS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        dif_fp = gpd.overlay(fp_projected, fp_base_projected, how="difference")

        # expansion cost (footprint)
        capital_factor_fp = assumptions["expansion_cost_a"]
        dif_fp_area = dif_fp.area.sum() / 1e6
        capital_fp = dif_fp_area * capital_factor_fp

        partial_fp[filename] = (
            fp_area,
            partial_sc,
            partial_hp,
            partial_sp,
            partial_cl,
            partial_dc,
            urban_expansion_area,
            partial_jobs,
            vg_area_loss,
            partial_solar,
            public_lighting_energy_consumption,
            cost_public_lighting,
            maintenance_fp,
            capital_fp,
        )

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=75)
    print(partial_fp)

    # Partial results TRANSIT ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
    partial_tr = {}

    for filename in transit:
        tr = gpd.read_file(path[2] + filename)
        tr_projected = tr.to_crs("World_Mollweide")
        tr_buffer = tr_projected.buffer(10)  # cambiar buffer i.e. 10m
        tr_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(tr_buffer))
        tr_buffer_area = tr_buffer.area.sum() / 1e6

        # __ASSUMPTIONS_
        maintenance_factor_tr = assumptions["mantainance_transit_cost_a"]

        tr_length = tr_projected.length.sum() / 1e3
        # tr_area = tr_buffer.area.sum() / 1e6
        maintenance_tr = tr_length * maintenance_factor_tr
        maintenance_tr = maintenance_tr * (2050 - 2025) / 1e6

        # CAPITAL COSTS |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        dif_tr = gpd.overlay(tr_buffer, tr_base_buffer, how="difference")

        # __ASSUMPTIONS_
        capital_factor_tr = assumptions["transit_cost_a"]

        # Get the new extension of the transit lines
        dif_tr_length = dif_tr.length.sum() / 1e3
        capital_tr = dif_tr_length * capital_factor_tr
        dif_tr_buffer = dif_tr.buffer(800)
        dif_tr_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(dif_tr_buffer))
        dif_tr_buffer_area = dif_tr_buffer.area.sum() / 1e6

        partial_tr[filename] = (
            dif_tr_buffer_area,
            tr_buffer_area,
            maintenance_tr,
            capital_tr,
        )

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=80)
    print(partial_tr)

    # Partial results PERMEABLE AREAS ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
    partial_perm = {}

    for filename in perm:
        # Read file & reproject geojson
        perm_gpd = gpd.read_file(path[12] + filename)
        perm_projected = perm_gpd.to_crs("World_Mollweide")
        # Get permeable area
        permeable_area = perm_projected.area.sum() / 1e6
        partial_perm[filename] = permeable_area

    partial_data_processed = {
        "partial_pop": partial_pop,
        "partial_nbs": partial_nbs,
        "partial_hp": partial_hp,
        "partial_sc": partial_sc,
        "partial_sp": partial_sp,
        "partial_cl": partial_cl,
        "partial_dc": partial_dc,
        "partial_UGA": partial_UGA,
        "partial_ht": partial_ht,
        "partial_fp": partial_fp,
        "partial_jobs": partial_jobs,
        "partial_solar": partial_solar,
        "partial_tr": partial_tr,
        "partial_perm": partial_perm,
        "density_base": density_base,
        "fp_base_area": fp_base_area,
        "pop_base": pop_base,
    }
    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=100)
    proyecto.partial_processing = make_serializable(partial_data_processed)
    proyecto.estatus = ProyectoStatus.READY
    proyecto.save()


# MAIN FUNCTION  ¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬
def urban_performance_partial(scenario, proyecto_pk, proyecto, assumptions):
    folder_path = proyecto.get_folder_path()
    working_dir = folder_path

    partial_pop = proyecto.partial_processing["partial_pop"]
    partial_nbs = proyecto.partial_processing["partial_nbs"]
    partial_hp = proyecto.partial_processing["partial_hp"]
    partial_sc = proyecto.partial_processing["partial_sc"]
    partial_sp = proyecto.partial_processing["partial_sp"]
    partial_cl = proyecto.partial_processing["partial_cl"]
    partial_dc = proyecto.partial_processing["partial_dc"]
    partial_UGA = proyecto.partial_processing["partial_UGA"]
    partial_ht = proyecto.partial_processing["partial_ht"]
    partial_fp = proyecto.partial_processing["partial_fp"]
    partial_jobs = proyecto.partial_processing["partial_jobs"]
    partial_solar = proyecto.partial_processing["partial_solar"]
    partial_tr = proyecto.partial_processing["partial_tr"]
    partial_perm = proyecto.partial_processing["partial_perm"]
    density_base = proyecto.partial_processing["density_base"]
    fp_base_area = proyecto.partial_processing["fp_base_area"]
    pop_base = proyecto.partial_processing["pop_base"]

    (
        pop_str,
        fp_str,
        tr_str,
        nbs_str,
        EE,
        solar_energy_p,
        rwh,
        hp_str,
        sc_str,
        sp,
        cl,
        dc,
        uga,
        inf,
        jobs,
        perm,
    ) = scenario

    # Extract all necessary data upfront to avoid multiple lookups
    (
        pop_2050,
        partial_nbs,
        partial_hp,
        partial_sc,
        partial_sp,
        partial_cl,
        partial_dc,
        partial_UGA,
        partial_ht,
    ) = partial_pop[pop_str]
    (
        exposed_area,
        exposed_pop,
        partial_nbs_tr,
        partial_nbs_hp,
        partial_nbs_sc,
        partial_nbs_infra,
        pc_exposed_pop,
        nbs_c_cost,
        nbs_m_cost,
        reconstruction_cost,
    ) = partial_nbs[nbs_str]
    pc_pop_hp = partial_hp[hp_str]
    pc_pop_sc = partial_sc[sc_str]
    pc_pop_sp = partial_sp[sp]
    pc_pop_cl = partial_cl[cl]
    pc_pop_dc = partial_dc[dc]
    uga_area, uga_per_capita, pc_pop_uga, ga_c_cost, ga_m_cost = partial_UGA[uga]
    pc_media_hu, pc_popular_hu, pc_residencial_hu = (
        partial_ht["Media_hu"],
        partial_ht["Popular_hu"],
        partial_ht["Residencial_hu"],
    )
    water_consumption, energy_consumption_water_supply = partial_ht[str(rwh)]

    (
        fp_area,
        partial_sc,
        partial_hp,
        partial_sp,
        partial_cl,
        partial_dc,
        urban_expansion_area,
        partial_jobs,
        vg_area_loss,
        partial_solar,
        public_lighting_energy_consumption,
        cost_public_lighting,
        maintenance_fp,
        capital_fp,
    ) = partial_fp[fp_str]
    total_sc, school_c_cost, school_m_cost, new_sc = partial_sc[sc_str]
    total_hp, hospital_c_cost, hospital_m_cost, new_hp = partial_hp[hp_str]
    total_sp, sport_c_cost, sport_m_cost, new_sp = partial_sp[sp]
    total_cl, clinic_c_cost, clinic_m_cost, new_cl = partial_cl[cl]
    total_dc, daycare_c_cost, daycare_m_cost, new_dc = partial_dc[dc]
    jobs_density = partial_jobs[jobs]
    solar_energy_generation, capital_solar_1, capital_solar = partial_solar[
        str(solar_energy_p)
    ]
    dif_tr_buffer_area, tr_buffer_area, maintenance_tr, capital_tr = partial_tr[tr_str]
    permeable_area = partial_perm[perm]

    # Calculate intermediary results
    pc_exposed_tr = partial_nbs_tr[tr_str]
    pc_exposed_infra = partial_nbs_infra[inf]
    count_hp_exposed = partial_nbs_hp[hp_str]
    count_sc_exposed = partial_nbs_sc[sc_str]
    density = pop_2050 / fp_area
    density_change = (density - density_base) / density_base

    # Electricity consumption
    elasticity_energy = assumptions["elasticity_energy"]
    energy_consumption_base = assumptions["energy_consumption_base"]
    energy_buildings_percentage = assumptions["energy_buildings_percentage"]
    change_electricity_consumption = -density_change * elasticity_energy
    electricity_consumption = energy_consumption_base * (
        1 + change_electricity_consumption / 100
    )
    electricity_consumption_buildings = electricity_consumption * (
        energy_buildings_percentage / 100
    )

    energy_used_ee = 100 - EE
    electricity_consumption_ee_b = electricity_consumption_buildings * (
        energy_used_ee / 100
    )
    electricity_consumption_ee = electricity_consumption_ee_b + (
        electricity_consumption - electricity_consumption_buildings
    )
    electricity_consumption_ee_per_capita = electricity_consumption_ee / pop_2050

    # GHG emissions
    # GHG emissions
    emissions_factor = assumptions["emissions_factor"]
    elasticity_emission = assumptions["elasticity_emissions"]
    emissions_transport_percentage = assumptions["emissions_transport_percentage"]
    ec_base_with_ee = energy_consumption_base * (energy_used_ee / 100)
    emissions_base_ee = ec_base_with_ee * emissions_factor
    change_in_emissions = -density_change * elasticity_emission
    emissions = emissions_base_ee * (1 + change_in_emissions / 100)
    emissions_tr = emissions * emissions_transport_percentage / 21
    # emissions_tr = emissions * (emissions_transport_percentage / 100)
    emissions_pc = emissions_tr / pop_2050
    pop_tr_adjust = pop_2050 * (dif_tr_buffer_area / fp_area)
    pop_other_adjust = pop_2050 - pop_tr_adjust
    emissions_tot_tr = (pop_tr_adjust * (emissions_pc * 0.75)) + (
        pop_other_adjust * emissions_pc
    )
    # emissions_tot_tr = (pop_2050 - tr_buffer_area / fp_area * pop_2050 * 0.15) * emissions_pc + tr_buffer_area / fp_area * pop_2050 * emissions_pc * 0.85
    transport_emissions_per_capita = emissions_tot_tr / pop_2050

    # VMT
    kvr_factor = assumptions["kvr"]
    VMT = assumptions["vmt"]
    expected_change = -density_change * VMT
    expected_vmt = kvr_factor * (1 + expected_change / 100)

    # Modal Distribution (KVR)
    modal_distribution_elasticity = assumptions["md_elasticity"]
    md_private = assumptions["md_tr"]
    md_public_transport = assumptions["md_w"]
    md_bicycle = assumptions["md_b"]
    expected_change_modal_distribution = density_change * modal_distribution_elasticity
    increase_public_transport = (
        md_public_transport - expected_change_modal_distribution * md_public_transport
    )
    public_tra_change = md_public_transport - increase_public_transport
    increase_bicycle = md_bicycle - expected_change_modal_distribution * md_bicycle
    bicycle_change = md_bicycle - increase_bicycle
    increase_private = md_private - public_tra_change - increase_bicycle

    # Maintenance and Capital Costs
    maintenance_cost = (
        maintenance_fp
        + maintenance_tr
        + hospital_m_cost
        + school_m_cost
        + sport_m_cost
        + clinic_m_cost
        + daycare_m_cost
        + ga_m_cost
        + cost_public_lighting
        + reconstruction_cost
    ) / 1e6
    capital_cost = (
        capital_fp
        + capital_tr
        + capital_solar
        + hospital_c_cost
        + school_c_cost
        + sport_c_cost
        + clinic_c_cost
        + daycare_c_cost
        + ga_c_cost
    ) / 1e6

    # Output Row
    row = [
        *scenario,
        fp_area,  # footprint area
        fp_base_area,  # base footprint area
        pop_2050,  # population 2050
        pop_base,  # base population
        exposed_area,  # area exposed to hazards #CHANGE
        pc_exposed_tr,  # percentage of roads exposed to hazards
        count_hp_exposed * 100 / total_hp,  # percentage of hospitals exposed to hazards
        count_sc_exposed * 100 / total_sc,  # percentage of schools exposed to hazards
        pc_exposed_infra,  # percentage of infrastructure exposed to hazards
        exposed_pop,  # total population exposed to hazards #CHANGE
        pc_exposed_pop,  # percentage of population exposed to hazards
        pc_pop_hp,  # percentage of population near a hospital
        pc_pop_sc,  # percentage of population near a school
        pc_pop_sp,  # percentage of population near a sport center
        pc_pop_cl,  # percentage of population near a clinic
        pc_pop_dc,  # percentage of population near a daycare
        pc_pop_uga,  # percentage of population near a green area
        density,  # hab/km2
        urban_expansion_area,  # urban expansion area
        jobs_density,  # jobs/km2
        vg_area_loss,  # vegetation cover loss #CHANGE
        permeable_area,  # permeable areas
        change_electricity_consumption,  # expected change in electricity consumption due to population density
        electricity_consumption,  # electricity consumption
        electricity_consumption_buildings,  # electricity consumption with buildings #CHANGE
        electricity_consumption_ee,  # electricity consumption with EE #CHANGE
        electricity_consumption_ee_per_capita,  # electricity consumption with EE per capita #CHANGE
        emissions_tot_tr,  # GHG emissions transport sector
        transport_emissions_per_capita,  # GHG emissions transport sector per capita #CHANGE
        solar_energy_generation / 1e6,  # potential solar energy generation
        public_lighting_energy_consumption / 1e6,  # public lighting energy consumption
        maintenance_fp / 1e6,  # maintenance cost footprint
        maintenance_tr / 1e6,  # maintenance cost transit
        maintenance_cost,  # maintenance cost total
        school_c_cost / 1e6,  # school capital cost
        new_sc,  # total number of new schools
        hospital_c_cost / 1e6,  # hospital capital cost
        new_hp,  # total number of new hospitals
        sport_c_cost / 1e6,  # sport center capital cost
        new_sp,  # total number of new sport centers
        clinic_c_cost / 1e6,  # clinic capital cost
        new_cl,  # total number of new clinics
        daycare_c_cost / 1e6,  # daycare center capital cost
        new_dc,  # total number of new daycare
        ga_c_cost / 1e6,  # green area capital cost
        capital_cost,  # capital cost total
        capital_solar_1,
        capital_solar,
        uga_area,  # total green area
        uga_per_capita,  # green area per capita #CHANGE
        kvr_factor * (1 + expected_change / 100),  # expected Modal Distribution (KVR)
        expected_vmt,  # VKT #CHANGE
        increase_bicycle,  # bicycle modal distribution
        increase_private,  # private vehicles modal distribution
        increase_public_transport,  # public transport modal distribution
        pc_media_hu,  # percentage of media housing type
        pc_popular_hu,  # percentage of popular housing type
        pc_residencial_hu,  # percentage of residential housing type
        water_consumption,  # total water consumption
        energy_consumption_water_supply,  # total energy water supply
    ]
    return row


@shared_task(soft_time_limit=30)
def process_scenario_chunk(
    scenario_chunk, proyecto_pk, timestamp, chunk_index, total_chunks
):
    results_batch = []
    proyecto = Proyecto.objects.get(pk=proyecto_pk)
    working_dir = proyecto.get_folder_path()

    query_template = """INSERT INTO urban_performance_controls ({cols}) VALUES {rows} ON CONFLICT (
        project_id,
        population_,
        footprint,
        transit,
        nbs,
        energy_efficiency,
        solar_energy,
        rwh,
        hospitals,
        schools,
        sport_centers,
        clinics,
        daycare,
        green_areas,
        infrastructure,
        jobs,
        permeable_areas
    ) DO UPDATE SET
        fp_area=EXCLUDED.fp_area,
        fp_base_area=EXCLUDED.fp_base_area,
        pop_2050=EXCLUDED.pop_2050,
        pop_base=EXCLUDED.pop_base,
        exposed_area=EXCLUDED.exposed_area,
        pc_exposed_tr=EXCLUDED.pc_exposed_tr,
        pc_exposed_hp=EXCLUDED.pc_exposed_hp,
        pc_exposed_sc=EXCLUDED.pc_exposed_sc,
        pc_exposed_infra=EXCLUDED.pc_exposed_infra,
        inter_pop=EXCLUDED.inter_pop,
        pc_exposed_pop=EXCLUDED.pc_exposed_pop,
        pc_pop_hp=EXCLUDED.pc_pop_hp,
        pc_pop_sc=EXCLUDED.pc_pop_sc,
        pc_pop_sp=EXCLUDED.pc_pop_sp,
        pc_pop_cl=EXCLUDED.pc_pop_cl,
        pc_pop_dc=EXCLUDED.pc_pop_dc,
        pc_pop_uga=EXCLUDED.pc_pop_uga,
        pop_density=EXCLUDED.pop_density,
        urban_expansion_area=EXCLUDED.urban_expansion_area,
        jobs_density=EXCLUDED.jobs_density,
        vg_area_loss=EXCLUDED.vg_area_loss,
        permeable_area=EXCLUDED.permeable_area,
        change_electricity_consumption=EXCLUDED.change_electricity_consumption,
        electricity_consumption=EXCLUDED.electricity_consumption,
        electricity_consumption_buildings=EXCLUDED.electricity_consumption_buildings,
        electricity_consumption_ee=EXCLUDED.electricity_consumption_ee,
        electricity_consumption_ee_per=EXCLUDED.electricity_consumption_ee_per_capita_capita,
        emissions_tot_tr=EXCLUDED.emissions_tot_tr,
        transport_emissions_per_capita=EXCLUDED.transport_emissions_per_capita,
        solar_energy_generation=EXCLUDED.solar_energy_generation,
        public_lighting_energy_consump=EXCLUDED.public_lighting_energy_consumptiontion,
        maintenance_fp=EXCLUDED.maintenance_fp,
        maintenance_tr=EXCLUDED.maintenance_tr,
        maintenance_cost=EXCLUDED.maintenance_cost,
        school_c_cost=EXCLUDED.school_c_cost,
        new_sc=EXCLUDED.new_sc,
        hospital_c_cost=EXCLUDED.hospital_c_cost,
        new_hp=EXCLUDED.new_hp,
        sp_c_cost=EXCLUDED.sp_c_cost,
        new_sp=EXCLUDED.new_sp,
        clinic_c_cost=EXCLUDED.clinic_c_cost,
        new_cl=EXCLUDED.new_cl,
        daycare_c_cost=EXCLUDED.daycare_c_cost,
        new_dc=EXCLUDED.new_dc,
        ga_c_cost=EXCLUDED.ga_c_cost,
        capital_cost=EXCLUDED.capital_cost,
        capital_solar_1=EXCLUDED.capital_solar_1,
        capital_solar=EXCLUDED.capital_solar,
        uga_area=EXCLUDED.uga_area,
        uga_per_capita=EXCLUDED.uga_per_capita,
        increased_kvr=EXCLUDED.increased_kvr,
        expected_vmt=EXCLUDED.expected_vmt,
        increase_bicycle=EXCLUDED.increase_bicycle,
        increase_private=EXCLUDED.increase_private,
        increase_public_transport=EXCLUDED.increase_public_transport,
        pc_media_hu=EXCLUDED.pc_media_hu,
        pc_popular_hu=EXCLUDED.pc_popular_hu,
        pc_residencial_hu=EXCLUDED.pc_residencial_hu,
        water_consumption=EXCLUDED.water_consumption,
        energy_consumption_water_supply=EXCLUDED.energy_consumption_water_supply
    ;"""

    assumptions_dir = working_dir + "/assumptions"
    assumptions = pd.read_csv(assumptions_dir + "/assumptions_SP.csv")

    # Convert values to int
    assumptions = dict(zip(assumptions["code"], assumptions["value"]))

    for scenario in scenario_chunk:
        try:
            result = urban_performance_partial(
                scenario, proyecto_pk, proyecto, assumptions
            )
            if result:
                results_batch.append(result)
        except Exception as e:
            # Log or handle exception if needed
            pass

    def save_batch(query: str):
        with connection.cursor() as cursor:
            try:
                cursor.execute(query)
            except Exception as error:
                print(f"Error while executing query: {error}")

    # If results exist, append them to the CSV file
    if results_batch:
        headers = [
            "project_id",
            "population_",
            "footprint",
            "transit",
            "nbs",
            "energy_efficiency",
            "solar_energy",
            "rwh",
            "hospitals",
            "schools",
            "sport_centers",
            "clinics",
            "daycare",
            "green_areas",
            "infrastructure",
            "jobs",
            "permeable_areas",
            "fp_area",
            "fp_base_area",
            "pop_2050",
            "pop_base",
            "exposed_area",
            "pc_exposed_tr",
            "pc_exposed_hp",
            "pc_exposed_sc",
            "pc_exposed_infra",
            "inter_pop",
            "pc_exposed_pop",
            "pc_pop_hp",
            "pc_pop_sc",
            "pc_pop_sp",
            "pc_pop_cl",
            "pc_pop_dc",
            "pc_pop_uga",
            "pop_density",
            "urban_expansion_area",
            "jobs_density",
            "vg_area_loss",
            "permeable_area",
            "change_electricity_consumption",
            "electricity_consumption",
            "electricity_consumption_buildings",
            "electricity_consumption_ee",
            "electricity_consumption_ee_per_capita",
            "emissions_tot_tr",
            "transport_emissions_per_capita",
            "solar_energy_generation",
            "public_lighting_energy_consumption",
            "maintenance_fp",
            "maintenance_tr",
            "maintenance_cost",
            "school_c_cost",
            "new_sc",
            "hospital_c_cost",
            "new_hp",
            "sp_c_cost",
            "new_sp",
            "clinic_c_cost",
            "new_cl",
            "daycare_c_cost",
            "new_dc",
            "ga_c_cost",
            "capital_cost",
            "capital_solar_1",
            "capital_solar",
            "uga_area",
            "uga_per_capita",
            "increased_kvr",
            "expected_vmt",
            "increase_bicycle",
            "increase_private",
            "increase_public_transport",
            "pc_media_hu",
            "pc_popular_hu",
            "pc_residencial_hu",
            "water_consumption",
            "energy_consumption_water_supply",
        ]
        batch = []
        for row in results_batch:
            row.insert(0, str(proyecto_pk))
            row = [
                f"'{value}'" if i <= len(headers) - 1 else str(float(value))
                for i, value in enumerate(row)
            ]
            batch.append(f"({','.join(row)})")
        query_final = query_template.format(
            cols=",".join(headers), rows=",".join(batch)
        )
        save_batch(query_final)
        batch.clear()

        # results_file = f"{working_dir}results_{timestamp}.csv"
        # with open(results_file, "a", newline="") as file:
        #     writer = csv.writer(file, delimiter=",")
        #     writer.writerows(results_batch)

    # progress from 40% to 80%
    new_progress = 40 + (40 * chunk_index / total_chunks)
    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=int(new_progress))

    return len(results_batch)  # Return the number of processed scenarios


def chunked_iterable(iterable, size):
    """Yield successive n-sized chunks from iterable."""
    iterator = iter(iterable)
    for first in iterator:  # Stops when iterator is empty
        yield list(islice(chain([first], iterator), size - 1))


@shared_task(soft_time_limit=300000)
def save_values(result: Any = None, proyecto_pk: str = ""):
    proyecto = Proyecto.objects.get(pk=proyecto_pk)
    folder_path = proyecto.get_folder_path()
    working_dir = folder_path

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=37)

    # Read assumptions from CSV file
    assumptions_dir = working_dir + "/assumptions"
    assumptions = pd.read_csv(assumptions_dir + "/assumptions_SP.csv")
    assumptions = dict(zip(assumptions["code"], assumptions["value"]))

    # Working directory folders
    working_folders = [
        "population/",
        "footprints/",
        "transit/",
        "nbs/",
        "hospitals/",
        "schools/",
        "sports/",
        "clinics/",
        "daycare/",
        "green areas/",
        "infraestructure/",
        "employment/",
        "permeable areas/",
    ]

    # Parameters for simulation
    energy_efficiency = [0, 20, 40]
    solar_energy = [0, 8.4, 5]
    RWH = [0, 50]

    # File reading
    path = [working_dir + folder for folder in working_folders]

    population = read_filenames_from_path(path[0])
    footprint = read_filenames_from_path(path[1])
    transit = read_filenames_from_path(path[2])
    nbs = read_filenames_from_path(path[3])
    hospitals = read_filenames_from_path(path[4])
    schools = read_filenames_from_path(path[5])
    sports = read_filenames_from_path(path[6])
    clinics = read_filenames_from_path(path[7])
    daycare = read_filenames_from_path(path[8])
    UGA = read_filenames_from_path(path[9])
    infra = read_filenames_from_path(path[10])
    jobs = read_filenames_from_path(path[11])
    perm = read_filenames_from_path(path[12])

    # # Prepare CSV file
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    # results_file = f"{working_dir}results_{timestamp}.csv"

    # # Check if CSV already exists to avoid overwriting
    # if not os.path.exists(results_file):
    #     with open(results_file, "w", newline="") as file:
    #         writer = csv.writer(file, delimiter=",")
    #         writer.writerow(header)

    # Iterables for scenarios
    iterables = [
        population,
        footprint,
        transit,
        nbs,
        energy_efficiency,
        solar_energy,
        RWH,
        hospitals,
        schools,
        sports,
        clinics,
        daycare,
        UGA,
        infra,
        jobs,
        perm,
    ]

    set_proyecto_progress(proyecto_pk=proyecto_pk, progress=40)

    # Generate the product of all iterables (scenarios)
    scenario_iter = product(*iterables)

    # Chunk size for each batch
    chunk_size = 100  # Adjust chunk size based on available memory

    # Calculate the total number of scenarios and chunks
    total_scenarios = (
        len(population)
        * len(footprint)
        * len(transit)
        * len(nbs)
        * len(energy_efficiency)
        * len(solar_energy)
        * len(RWH)
        * len(hospitals)
        * len(schools)
        * len(sports)
        * len(clinics)
        * len(daycare)
        * len(UGA)
        * len(infra)
        * len(jobs)
        * len(perm)
    )
    total_chunks = (
        total_scenarios + chunk_size - 1
    ) // chunk_size  # Total number of chunks

    # Group tasks for Celery to handle in parallel, passing chunk_index and total_chunks
    scenario_chunks = chunked_iterable(scenario_iter, chunk_size)
    task_group = group(
        process_scenario_chunk.s(chunk, proyecto_pk, timestamp, idx, total_chunks)
        for idx, chunk in enumerate(scenario_chunks)
    )

    # Process all chunks in parallel using Celery
    task_group.apply_async()

    # Return task ID or other information for tracking progress
    return f"Started processing scenarios for proyecto {proyecto_pk}."
