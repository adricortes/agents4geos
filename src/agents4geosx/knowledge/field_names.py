"""Solver type → valid FieldSpecification field names mapping.

Also documents SourceFlux behavior and composition initialization patterns.
"""

SOLVER_FIELD_NAMES: dict[str, list[str]] = {
    "SinglePhaseFVM": ["pressure", "temperature"],
    "SinglePhaseHybridFVM": ["pressure", "temperature"],
    "SinglePhaseReservoir": ["pressure", "temperature"],
    "CompositionalMultiphaseFVM": ["pressure", "globalCompFraction", "temperature"],
    "CompositionalMultiphaseHybridFVM": ["pressure", "globalCompFraction", "temperature"],
    "CompositionalMultiphaseReservoir": ["pressure", "globalCompFraction", "temperature"],
    "ImmiscibleMultiphaseFlow": ["pressure", "phaseVolumeFraction", "temperature"],
}

# SourceFlux does NOT have a fieldName attribute.
# It implicitly applies a mass/volume flux.
# For compositional flows, it has a `component` attribute (0-indexed) to specify
# which component's mass flux is being set.
SOURCEFLUX_INFO = {
    "has_fieldName": False,
    "required_attrs": ["name", "objectPath", "scale", "setNames"],
    "optional_attrs": ["component"],  # 0-indexed component for compositional
    "notes": "scale is mass rate (kg/s). Negative = injection, positive = production.",
}

# Composition initialization pattern for compositional flows:
# Each component needs a separate FieldSpecification with component="0", "1", etc.
# The component fractions MUST sum to ~1.0.
# Example for CO2-brine (2 components):
#   component="0" → CO2 fraction (e.g., 0.005)
#   component="1" → water fraction (e.g., 0.995)
COMPOSITION_INIT_NOTES = (
    "For compositional flows, initialize globalCompFraction with one FieldSpecification "
    "per component using the component attribute (0-indexed). Fractions must sum to ~1.0."
)


def get_field_names(solver_type: str) -> list[str]:
    return SOLVER_FIELD_NAMES.get(solver_type, ["pressure"])
