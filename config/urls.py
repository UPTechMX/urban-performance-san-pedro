# ruff: noqa
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path, re_path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from django.views.static import serve
from urban_performance.projects.views import ProjectListView
from django.conf.urls.i18n import i18n_patterns
from urban_performance.projects.models import Proyecto
from django.shortcuts import redirect, reverse
from django.utils.translation import activate

def redirect_to_san_pedro(request):
    activate('es-mx')
    project = Proyecto.objects.get(nombre="implang")
    url = reverse('projects:project_detail', kwargs={'pk': project.pk})
    return redirect(url)

urlpatterns = [
    # User management
    path("api/v1/", include("urban_performance.api.urls", namespace="api")),
    path('implang/', redirect_to_san_pedro, name='redirect_to_project'),
    # Your stuff: custom urls includes go here
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

urlpatterns += i18n_patterns(
    path("", view=ProjectListView.as_view(), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    path("users/", include("urban_performance.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    path("projects/", include("urban_performance.projects.urls", namespace="projects")),
)

if not settings.DEBUG:
    static_urlpatterns = [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
        re_path(
            r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}
        ),
    ]
    urlpatterns += static_urlpatterns

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
