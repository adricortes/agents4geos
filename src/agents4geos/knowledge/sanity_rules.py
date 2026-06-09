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

# Coupled solid types that GEOS recognizes in materialList.
# Every CellElementRegion materialList MUST include one of these.
COUPLED_SOLID_TYPES = {
    "CompressibleSolidConstantPermeability",
    "CompressibleSolidCarmanKozenyPermeability",
    "CompressibleSolidPressurePermeability",
    "CompressibleSolidSlipDependentPermeability",
    "PorousElasticIsotropic",
    "PorousElasticIsotropicCarmanKozenyPermeability",
    "ThermoPoroElasticIsotropic",
}


# Structural validation rules beyond physics heuristics.
# These check document structure patterns that the XSD schema alone cannot enforce.
STRUCTURAL_RULES: list[dict] = [
    {
        "name": "required_attributes",
        "description": "REQUIRED attributes (InputFlags) must be present",
        "severity": "error",
    },
    {
        "name": "redundant_defaults",
        "description": "Attributes matching schema default values are redundant",
        "severity": "advisory",
    },
    {
        "name": "empty_elements",
        "description": "Elements with no required children and no actual children may be unnecessary",
        "severity": "advisory",
    },
]


def _parse_numeric_values(raw: str) -> list[float]:
    """Parse a GEOS attribute value into the numbers it contains.

    Handles scalars ("1e-16") and flat GEOS list literals ("{ 1e-16, 1e-16 }").
    Non-numeric tokens (units, expressions, names) are skipped; an all-non-numeric
    value yields an empty list so the caller can skip it.
    """
    s = raw.strip()
    if s.startswith("{") and s.endswith("}"):
        tokens = s[1:-1].split(",")
    else:
        tokens = [s]
    values: list[float] = []
    for tok in tokens:
        try:
            values.append(float(tok.strip()))
        except (ValueError, TypeError):
            pass
    return values


def run_sanity_checks(attributes: list[tuple[str, str]]) -> list[dict]:
    """Run physics sanity checks on (attribute_name, value) pairs.

    Takes a list of pairs rather than a dict so that identically-named attributes
    on different elements (e.g. two `referencePressure`) are each evaluated instead
    of colliding. The rule pattern is matched case-insensitively, and GEOS list
    literals ("{ a, b, c }") are checked component-wise.

    Returns list of {name, attribute, value, status, message}.
    """
    results = []
    for rule in SANITY_RULES:
        pattern = rule["attribute_pattern"].lower()
        for attr_name, attr_value in attributes:
            if pattern not in attr_name.lower():
                continue
            values = _parse_numeric_values(attr_value)
            if not values:
                continue  # Non-numeric or expression — skip
            bad = [v for v in values if not (rule["min"] <= v <= rule["max"])]
            results.append({
                "name": rule["name"],
                "attribute": attr_name,
                "value": values[0] if len(values) == 1 else values,
                "status": "fail" if bad else "pass",
                "message": "OK" if not bad else rule["message"],
            })
    return results


def check_document_structure(root_element) -> list[dict]:
    """Run structural checks on the full document.

    Checks:
    - Every CellElementRegion materialList includes a coupled solid
    - Composition fractions sum to ~1.0
    """
    results = []

    # Check coupled solid in materialList
    for section in root_element.children:
        if section.schema_element.name == "ElementRegions":
            for region in section.children:
                if region.schema_element.name == "CellElementRegion":
                    mat_list = region.attributes.get("materialList", "")
                    region_name = region.attributes.get("name", "unknown")
                    # Parse material names from "{ name1, name2 }"
                    if mat_list.startswith("{") and mat_list.endswith("}"):
                        names = [n.strip() for n in mat_list[1:-1].split(",")]
                    else:
                        names = [mat_list.strip()]
                    results.append({
                        "name": "materialList_has_names",
                        "attribute": f"ElementRegions/{region_name}/materialList",
                        "status": "pass" if len(names) >= 2 else "fail",
                        "message": "OK" if len(names) >= 2 else
                                   f"materialList should have at least fluid + coupled solid, got: {names}",
                    })

    # Check composition initialization sums
    comp_fractions: dict[str, float] = {}  # setName → sum of component fractions
    for section in root_element.children:
        if section.schema_element.name == "FieldSpecifications":
            for spec in section.children:
                field = spec.attributes.get("fieldName", "")
                if field == "globalCompFraction" and spec.attributes.get("initialCondition") == "1":
                    set_names = spec.attributes.get("setNames", "all")
                    try:
                        scale = float(spec.attributes.get("scale", "0"))
                        comp_fractions[set_names] = comp_fractions.get(set_names, 0.0) + scale
                    except (ValueError, TypeError):
                        pass

    for set_name, total in comp_fractions.items():
        passed = 0.99 <= total <= 1.01
        results.append({
            "name": "composition_sum",
            "attribute": f"globalCompFraction on {set_name}",
            "value": total,
            "status": "pass" if passed else "fail",
            "message": "OK" if passed else f"Component fractions sum to {total:.4f}, should be ~1.0",
        })

    return results
