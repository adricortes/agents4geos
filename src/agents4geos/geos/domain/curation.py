"""Field grouping and display ordering per element type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FieldGroup:
    """A logical group of fields for display in the TUI."""

    label: str
    field_names: list[str]


# Keyed by complex type name (e.g., "SinglePhaseFVMType")
_FIELD_GROUPS: dict[str, list[FieldGroup]] = {
    "SinglePhaseFVMType": [
        FieldGroup("Essential", ["name", "discretization", "targetRegions"]),
        FieldGroup("Physics", ["isThermal", "temperature", "allowNegativePressure"]),
        FieldGroup("Time Stepping", ["cflFactor", "initialDt"]),
        FieldGroup("Advanced", [
            "logLevel", "writeLinearSystem", "writeStatistics",
            "maxAbsolutePressureChange", "maxSequentialPressureChange",
            "maxSequentialTemperatureChange", "usePhysicsScaling",
            "allowNonConvergedLinearSolverSolution",
        ]),
    ],
    "CompositionalMultiphaseFVMType": [
        FieldGroup("Essential", ["name", "discretization", "targetRegions"]),
        FieldGroup("Physics", ["isThermal", "temperature", "useMass"]),
        FieldGroup("Composition", ["maxCompFractionChange"]),
        FieldGroup("Time Stepping", ["cflFactor", "initialDt"]),
        FieldGroup("Advanced", ["logLevel", "writeLinearSystem", "writeStatistics"]),
    ],
    "CompressibleSinglePhaseFluidType": [
        FieldGroup("Essential", ["name", "defaultDensity", "defaultViscosity"]),
        FieldGroup("Reference State", [
            "referencePressure", "referenceDensity", "referenceViscosity",
        ]),
        FieldGroup("Compressibility", [
            "compressibility", "viscosibility",
            "densityModelType", "viscosityModelType",
        ]),
    ],
    "InternalMeshType": [
        FieldGroup("Essential", ["name", "elementTypes", "cellBlockNames"]),
        FieldGroup("X Direction", ["xCoords", "nx"]),
        FieldGroup("Y Direction", ["yCoords", "ny"]),
        FieldGroup("Z Direction", ["zCoords", "nz"]),
    ],
}


def get_field_groups(type_name: str) -> list[FieldGroup]:
    """Get curated field groups for a complex type, or empty list if uncurated."""
    return _FIELD_GROUPS.get(type_name, [])
