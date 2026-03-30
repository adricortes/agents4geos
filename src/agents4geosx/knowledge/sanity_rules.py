"""Physics heuristic sanity checks for GEOS input parameters."""

from __future__ import annotations

SANITY_RULES: list[dict] = [
    {
        "name": "permeability_range",
        "attribute_pattern": "permeability",
        "min": 1e-20, "max": 1e-8,
        "unit": "m^2",
        "message": "Permeability should be between 1e-20 and 1e-8 m^2 for reservoir rock",
    },
    {
        "name": "porosity_range",
        "attribute_pattern": "referencePorosity",
        "min": 0.001, "max": 0.5,
        "unit": "fraction",
        "message": "Porosity should be between 0.1% and 50%",
    },
    {
        "name": "pressure_positive",
        "attribute_pattern": "pressure",
        "min": 0, "max": 1e10,
        "unit": "Pa",
        "message": "Pressure must be positive and below 10 GPa",
    },
    {
        "name": "temperature_range",
        "attribute_pattern": "temperature",
        "min": 273, "max": 573,
        "unit": "K",
        "message": "Temperature should be between 0C and 300C for subsurface",
    },
    {
        "name": "cfl_range",
        "attribute_pattern": "cflFactor",
        "min": 0, "max": 1,
        "unit": "dimensionless",
        "message": "CFL factor must be in (0, 1]",
    },
]


def run_sanity_checks(attributes: dict[str, str]) -> list[dict]:
    """Run physics sanity checks on attribute values.

    Returns list of {name, attribute, value, status, message}.
    """
    results = []
    for rule in SANITY_RULES:
        pattern = rule["attribute_pattern"]
        matching = {k: v for k, v in attributes.items() if pattern in k.lower()}
        for attr_name, attr_value in matching.items():
            try:
                value = float(attr_value)
                passed = rule["min"] <= value <= rule["max"]
                results.append({
                    "name": rule["name"],
                    "attribute": attr_name,
                    "value": value,
                    "status": "pass" if passed else "fail",
                    "message": "OK" if passed else rule["message"],
                })
            except (ValueError, TypeError):
                pass  # Non-numeric or expression — skip
    return results
