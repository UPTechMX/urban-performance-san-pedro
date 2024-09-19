import pandas as pd

from rest_framework import serializers
from .models import Proyecto, Control, Indicador, Escenario
from .validators import validate_escenario_structure
from django.contrib.auth import get_user_model
from urban_performance.projects import utils
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class ProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proyecto
        fields = [
            "nombre",
            "descripcion",
            "ciudad",
            "uso_como_template",
            "assumptions",
            "estatus",
        ]

    def create(self, validated_data):
        proyecto = Proyecto.objects.create(
            **validated_data,
            creado_por=User.objects.get(pk=self.context["request"].user.pk),
        )
        return proyecto

    def is_valid(self, raise_exception=False):
        # Call the parent class's is_valid method
        valid = super().is_valid(raise_exception=raise_exception)

        # Add custom validation for "assumptions"
        assumptions = self.initial_data.get("assumptions")

        if not self.partial or (self.partial and assumptions):
            try:
                # Assuming assumptions is a file-like object
                df = pd.read_csv(assumptions)
                is_valid_assumptions = utils.validate_assumptions_df(
                    df=df, request=self.context["request"]
                )
                if not is_valid_assumptions:
                    self._errors["assumptions"] = [_("Invalid assumptions data")]
                    valid = False
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._errors["assumptions"] = [
                    _("Please introduce a valid CSV file.")
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


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = "__all__"


class IndicadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicador
        fields = "__all__"


class EscenarioSerializer(serializers.ModelSerializer):
    structure = serializers.JSONField(validators=[validate_escenario_structure])

    class Meta:
        model = Escenario
        fields = "__all__"


class AssumptionsSerializer(serializers.Serializer):
    data = serializers.JSONField(required=True)
