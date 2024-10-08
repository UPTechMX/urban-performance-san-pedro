create table public.urban_performance_controls (
    id integer generated always as identity unique,
    project_id uuid not null,
    population_ text not null,
    footprint text not null,
    transit text not null,
    nbs text not null,
    energy_efficiency double precision not null,
    solar_energy double precision not null,
    rwh text not null,
    hospitals text not null,
    schools text not null,
    sport_centers text not null,
    clinics text not null,
    daycare text not null,
    green_areas text not null,
    infrastructure text not null,
    jobs text not null,
    permeable_areas text not null,
    fp_area double precision not null,
    fp_base_area double precision not null,
    pop_2050 double precision not null,
    pop_base double precision not null,
    exposed_area double precision not null,
    pc_exposed_tr double precision not null,
    pc_exposed_hp double precision not null,
    pc_exposed_sc double precision not null,
    pc_exposed_infra double precision not null,
    inter_pop double precision not null,
    pc_exposed_pop double precision not null,
    pc_pop_hp double precision not null,
    pc_pop_sc double precision not null,
    pc_pop_sp double precision not null,
    pc_pop_cl double precision not null,
    pc_pop_dc double precision not null,
    pc_pop_uga double precision not null,
    pop_density double precision not null,
    urban_expansion_area double precision not null,
    jobs_density double precision not null,
    vg_area_loss double precision not null,
    permeable_area double precision not null,
    change_electricity_consumption double precision not null,
    electricity_consumption double precision not null,
    electricity_consumption_buildings double precision not null,
    electricity_consumption_ee double precision not null,
    electricity_consumption_ee_per_capita double precision not null,
    emissions_tot_tr double precision not null,
    transport_emissions_per_capita double precision not null,
    solar_energy_generation double precision not null,
    public_lighting_energy_consumption double precision not null,
    maintenance_fp double precision not null,
    maintenance_tr double precision not null,
    maintenance_cost double precision not null,
    school_c_cost double precision not null,
    new_sc double precision not null,
    hospital_c_cost double precision not null,
    new_hp double precision not null,
    sp_c_cost double precision not null,
    new_sp double precision not null,
    clinic_c_cost double precision not null,
    new_cl double precision not null,
    daycare_c_cost double precision not null,
    new_dc double precision not null,
    ga_c_cost double precision not null,
    capital_cost double precision not null,
    capital_solar_1 double precision not null,
    capital_solar double precision not null,
    uga_area double precision not null,
    uga_per_capita double precision not null,
    increased_kvr double precision not null,
    expected_vmt double precision not null,
    increase_bicycle double precision not null,
    increase_private double precision not null,
    increase_public_transport double precision not null,
    pc_media_hu double precision not null,
    pc_popular_hu double precision not null,
    pc_residencial_hu double precision not null,
    water_consumption double precision not null,
    energy_consumption_water_supply double precision not null,
    constraint urban_performance_controls_project_id_population__footprint_transit_nbs_en_key unique (
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
    )
);

alter table
    public.urban_performance_controls owner to postgres;

create index idx_urban_performance_controls_project_id on public.urban_performance_controls (project_id);

create index idx_urban_performance_controls_population_ on public.urban_performance_controls (population_);

create index idx_urban_performance_controls_footprint on public.urban_performance_controls (footprint);

create index idx_urban_performance_controls_transit on public.urban_performance_controls (transit);

create index idx_urban_performance_controls_nbs on public.urban_performance_controls (nbs);

create index idx_urban_performance_controls_hospitals on public.urban_performance_controls (hospitals);

create index idx_urban_performance_controls_schools on public.urban_performance_controls (schools);

create index idx_urban_performance_controls_sports_centers on public.urban_performance_controls (sport_centers);

create index idx_urban_performance_controls_clinics on public.urban_performance_controls (clinics);

create index idx_urban_performance_controls_daycare on public.urban_performance_controls (daycare);

create index idx_urban_performance_controls_green_areas on public.urban_performance_controls (green_areas);

create index idx_urban_performance_controls_infrastructure on public.urban_performance_controls (infrastructure);

create index idx_urban_performance_controls_jobs on public.urban_performance_controls (jobs);

create index idx_urban_performance_controls_permeable_areas on public.urban_performance_controls (permeable_areas);

create index idx_urban_performance_controls_energy_efficiency on public.urban_performance_controls (energy_efficiency);

create index idx_urban_performance_controls_solar_energy on public.urban_performance_controls (solar_energy);

create index idx_urban_performance_controls_rwh on public.urban_performance_controls (rwh);