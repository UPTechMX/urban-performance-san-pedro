from django.contrib import admin
from .models import Proyecto, Control, Indicador, Escenario


class ProyectoAdmin(admin.ModelAdmin):
    pass


class ControlAdmin(admin.ModelAdmin):
    pass


class IndicadorAdmin(admin.ModelAdmin):
    pass


class EscenarioAdmin(admin.ModelAdmin):
    pass


admin.site.register(Proyecto, ProyectoAdmin)
admin.site.register(Control, ControlAdmin)
admin.site.register(Indicador, IndicadorAdmin)
admin.site.register(Escenario, EscenarioAdmin)
