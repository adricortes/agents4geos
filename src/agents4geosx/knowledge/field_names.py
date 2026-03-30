"""Solver type → valid FieldSpecification field names mapping."""

SOLVER_FIELD_NAMES: dict[str, list[str]] = {
    "SinglePhaseFVM": ["pressure", "temperature"],
    "SinglePhaseHybridFVM": ["pressure", "temperature"],
    "SinglePhaseReservoir": ["pressure", "temperature"],
    "CompositionalMultiphaseFVM": ["pressure", "globalCompFraction", "temperature"],
    "CompositionalMultiphaseHybridFVM": ["pressure", "globalCompFraction", "temperature"],
    "CompositionalMultiphaseReservoir": ["pressure", "globalCompFraction", "temperature"],
    "ImmiscibleMultiphaseFlow": ["pressure", "phaseVolumeFraction", "temperature"],
}


def get_field_names(solver_type: str) -> list[str]:
    return SOLVER_FIELD_NAMES.get(solver_type, ["pressure"])
