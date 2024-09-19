from django.contrib import admin
from .models import SpatialFile

# Register your models here.
class SpatialFileAdmin(admin.ModelAdmin):
    pass

admin.site.register(SpatialFile, SpatialFileAdmin)