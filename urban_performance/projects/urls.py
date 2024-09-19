from django.urls import path, re_path

from urban_performance.projects import views

app_name = "projects"
urlpatterns = [
    path("list/", view=views.ProjectListView.as_view(), name="project_list"),
    path("delete/<pk>/", view=views.ProjectDeleteView.as_view(), name="project_delete"),
    path("<pk>/", view=views.ProjectDetailView.as_view(), name="project_detail"),
    path("dowload/<pk>/", view=views.download_project_files, name="download_project_files"),
    re_path(r"^geo_json/(?P<path>.*)$", view=views.convert_geojson, name="download_project_files"),
]
