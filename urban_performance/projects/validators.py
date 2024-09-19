import jsonschema
from rest_framework import exceptions

escenarios_schema = {
    "type": "object",
    "properties": {
        "controles": {
            "type": "object",
            "properties": {
                "population_": {"type": "string"},
                "nbs": {"type": "string"},
                "transit": {"type": "string"},
                "footprint": {"type": "string"},
                "energy_efficiency": {"type": "number"},
                "clinics": {"type": "string"},
                "green_areas": {"type": "string"},
                "hospitals": {"type": "string"},
                "infrastructure": {"type": "string"},
                "jobs": {"type": "string"},
                "permeable_areas": {"type": "string"},
                "rwh": {"type": "number"},
                "solar_energy": {"type": "number"},
                "schools": {"type": "string"},
                "transit": {"type": "string"},
                "sport_centers": {"type": "string"},
            },
        }
    },
    "required": ["controles"],
}


def validate_escenario_structure(value):
    try:
        schema = jsonschema.Draft7Validator(escenarios_schema)
        schema.validate(value)
    except jsonschema.ValidationError as e:
        raise exceptions.ValidationError(e.message)
