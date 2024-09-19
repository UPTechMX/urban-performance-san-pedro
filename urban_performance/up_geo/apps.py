import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UpGeoConfig(AppConfig):
    name = "urban_performance.up_geo"
    verbose_name = _("UP Geo")

    def ready(self):
        with contextlib.suppress(ImportError):
            import urban_performance.up_geo.signals  # noqa: F401
