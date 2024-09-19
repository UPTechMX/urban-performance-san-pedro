import json

from rest_framework import serializers
from .models import SpatialFile
from django.utils.translation import gettext_lazy as _


class SpatialFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpatialFile
        fields = ["pk", "proyecto", "nombre", "tipo", "descripcion", "archivo"]

    def is_valid(self, raise_exception=False):
        # Call the parent class's is_valid method
        valid = super().is_valid(raise_exception=raise_exception)

        # Add custom validation for "archivo"
        archivo = self.initial_data.get("archivo")

        if not self.partial or (self.partial and archivo):
            if not archivo.name.endswith(".geojson"):
                self._errors["archivo"] = [_("File extension must be .geojson")]
                valid = False
            else:
                try:
                    content = archivo.read().decode("utf-8")
                    geojson = json.loads(content)
                    # You can add more specific geojson validation logic here if needed
                    if "type" not in geojson or geojson["type"] != "FeatureCollection":
                        self._errors["archivo"] = [
                            _("The file content is not a valid GeoJSON")
                        ]
                        valid = False
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    self._errors[f"File {self.initial_data.get('nombre')}"] = [
                        _("Invalid GeoJSON file")
                    ]
                    valid = False

        if raise_exception and not valid:
            raise serializers.ValidationError(self.errors)

        return valid

    @property
    def custom_full_errors(self):
        """
        Returns full errors formatted as per requirements
        """
        default_errors = self.errors  # default errors dict
        errors_messages = []
        for field_name, field_errors in default_errors.items():
            for field_error in field_errors:
                error_message = "%s: %s" % (field_name, field_error)
                errors_messages.append(
                    error_message
                )  # append error message to 'errors_messages'
        return errors_messages
