import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    name = "urban_performance.api"
    verbose_name = _("API")

    def ready(self):
        with contextlib.suppress(ImportError):
            import urban_performance.projects.signals  # noqa: F401
