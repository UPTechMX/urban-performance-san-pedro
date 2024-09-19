import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    name = "urban_performance.projects"
    verbose_name = _("Projects")

    def ready(self):
        with contextlib.suppress(ImportError):
            import urban_performance.projects.signals  # noqa: F401
