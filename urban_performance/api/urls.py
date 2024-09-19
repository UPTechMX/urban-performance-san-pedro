from django.urls import path
from .views import (
    ProyectoViewSet,
    SpatialFileViewSet,
    ControlViewSet,
    IndicadorViewSet,
    EscenarioViewSet,
    OpcionesView,
    BaseEscenarioViewSet,
    FilterUpControlsView,
)

app_name = "api"

urlpatterns = [
    path(
        "proyectos/<pk>/update_assumptions/",
        ProyectoViewSet.as_view({"post": "update_assumptions"}),
        name="update-assumptions",
    ),
    path(
        "proyectos/",
        ProyectoViewSet.as_view({"get": "list", "post": "create"}),
        name="proyecto-list",
    ),
    path(
        "proyectos/<uuid:pk>/",
        ProyectoViewSet.as_view(
            {"get": "retrieve", "put": "update"}
        ),
        name="proyecto-detail",
    ),
    path(
        "proyectos/<uuid:proyecto_pk>/archivos-espaciales/",
        SpatialFileViewSet.as_view({"get": "list", "post": "create"}),
        name="spatialfile-list",
    ),
    path(
        "proyectos/<uuid:proyecto_pk>/archivos-espaciales/<int:pk>/",
        SpatialFileViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="spatialfile-detail",
    ),
    path(
        "proyectos/<uuid:proyecto_pk>/opciones/",
        OpcionesView.as_view({"get": "get"}),
        name="opciones-proyecto",
    ),
    path(
        "proyectos/<uuid:proyecto_pk>/controles/",
        ControlViewSet.as_view({"get": "list", "post": "create"}),
        name="control-list",
    ),
    path(
        "controles/<int:pk>/",
        ControlViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="control-detail",
    ),
    path(
        "proyectos/<uuid:proyecto_pk>/indicadores/",
        IndicadorViewSet.as_view({"get": "list", "post": "create"}),
        name="indicador-list",
    ),
    path(
        "indicadores/<int:pk>/",
        IndicadorViewSet.as_view(
            {"get": "retrieve", "post": "update", "patch": "patch", "delete": "destroy"}
        ),
        name="indicador-detail",
    ),
    path(
        "proyectos/<uuid:proyecto>/escenarios/",
        EscenarioViewSet.as_view({"get": "list", "post": "create"}),
        name="escenario-list",
    ),
    path(
        "escenarios/<int:pk>/",
        BaseEscenarioViewSet.as_view(
            {"patch": "update", "delete": "destroy"}
        ),
        name="escenario-detail",
    ),
    path(
        "filter-controls/<uuid:proyecto_pk>/",
        FilterUpControlsView.as_view(),
        name="filter-controls",
    ),
]
