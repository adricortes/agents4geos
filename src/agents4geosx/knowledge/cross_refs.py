"""Element cross-reference definitions."""

from __future__ import annotations

ATTRIBUTE_REFERENCES: dict[str, dict] = {
    "discretization": {"target_section": "NumericalMethods", "description": "References a discretization method by name"},
    "targetRegions": {"target_section": "ElementRegions", "description": "References element region names"},
    "materialList": {"target_section": "Constitutive", "description": "References constitutive model names"},
    "setNames": {"target_section": "Geometry", "description": "References geometry box names"},
    "functionName": {"target_section": "Functions", "description": "References a TableFunction by name"},
    "wellControlsName": {"target_section": "Solvers", "description": "References WellControls"},
    "wellSolverName": {"target_section": "Solvers", "description": "References a well solver"},
    "flowSolverName": {"target_section": "Solvers", "description": "References a flow solver"},
    "solidSolverName": {"target_section": "Solvers", "description": "References a solid mechanics solver"},
    "solidModelName": {"target_section": "Constitutive", "description": "References a solid model"},
    "porosityModelName": {"target_section": "Constitutive", "description": "References a porosity model"},
    "permeabilityModelName": {"target_section": "Constitutive", "description": "References a permeability model"},
    "solidInternalEnergyModelName": {"target_section": "Constitutive", "description": "References a SolidInternalEnergy model (thermal coupling)"},
}


def get_cross_references(element_name: str, attributes: list) -> list[dict]:
    """Return cross-references for an element based on its attributes."""
    refs = []
    for attr in attributes:
        if attr.name in ATTRIBUTE_REFERENCES:
            ref_info = ATTRIBUTE_REFERENCES[attr.name]
            refs.append({
                "attribute": attr.name,
                "target_section": ref_info["target_section"],
                "description": ref_info["description"],
            })
    return refs
