"""Fallback descriptions for elements and attributes where XSD comments are missing."""

from __future__ import annotations

# Keyed by element name, then attribute name (or "_element" for element-level)
FALLBACK_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "SinglePhaseFVM": {
        "_element": "Finite volume method solver for single-phase fluid flow through porous media.",
        "cflFactor": "Courant-Friedrichs-Lewy factor for adaptive time stepping. Values in (0, 1].",
        "discretization": "Name of the numerical discretization (defined in NumericalMethods).",
        "targetRegions": "Element regions where this solver is applied.",
    },
    "SinglePhaseHybridFVM": {
        "_element": "Hybrid finite volume solver for single-phase flow with improved accuracy on non-orthogonal grids.",
    },
    "CompositionalMultiphaseFVM": {
        "_element": "Finite volume solver for compositional multiphase flow (including CO2-brine systems).",
    },
    "CompositionalMultiphaseHybridFVM": {
        "_element": "Hybrid finite volume solver for compositional multiphase flow.",
    },
    "CompositionalMultiphaseReservoir": {
        "_element": "Coupled reservoir solver combining compositional multiphase flow with wells.",
    },
    "SinglePhaseReservoir": {
        "_element": "Coupled reservoir solver combining single-phase flow with wells.",
    },
    "SinglePhaseWell": {
        "_element": "Well solver for single-phase flow, used as a child of SinglePhaseReservoir.",
    },
    "CompositionalMultiphaseWell": {
        "_element": "Well solver for compositional multiphase flow.",
    },
    "ImmiscibleMultiphaseFlow": {
        "_element": "Solver for immiscible multiphase flow (phases do not mix).",
    },
    "CompressibleSinglePhaseFluid": {
        "_element": "Single-phase compressible fluid model with configurable density and viscosity models.",
    },
    "CO2BrinePhillipsFluid": {
        "_element": "CO2-brine fluid model using the Phillips correlation for mutual solubility.",
    },
    "CO2BrineEzrokhiFluid": {
        "_element": "CO2-brine fluid model using the Ezrokhi correlation.",
    },
    "InternalMesh": {
        "_element": "Structured mesh generator for simple geometries (boxes, cylinders).",
    },
    "VTKMesh": {
        "_element": "Import an unstructured mesh from a VTK file.",
    },
    "BrooksCoreyRelativePermeability": {
        "_element": "Brooks-Corey relative permeability model.",
    },
    "VanGenuchtenCapillaryPressure": {
        "_element": "Van Genuchten capillary pressure model.",
    },
    "ConstantPermeability": {
        "_element": "Constant (homogeneous) permeability model.",
    },
}


def get_description(
    element_name: str,
    attribute_name: str | None,
    schema_description: str,
) -> str:
    """Get the best available description for an element or attribute.

    Priority: schema_description > fallback > empty string.
    """
    if schema_description:
        return schema_description

    fallbacks = FALLBACK_DESCRIPTIONS.get(element_name, {})
    key = attribute_name if attribute_name else "_element"
    fallback = fallbacks.get(key, "")
    if fallback:
        return fallback

    # Element-level fallback if attribute not found
    if attribute_name and not fallback:
        return fallbacks.get("_element", "")

    return ""
