"""V1 scope definitions — which solvers and constitutive models are supported.

Only elements listed here are shown as selectable in the TUI.
Deferred (out-of-scope) elements that appear in a loaded XML file should be
preserved and displayed read-only with a "not yet supported" label.

Sections not listed here (Mesh, Events, Geometry, NumericalMethods,
ElementRegions, FieldSpecifications, Functions, Outputs, Tasks, Parameters,
Included) show all schema children without filtering.
"""

from __future__ import annotations

from agents4geos.geos.schema.model import SchemaElement

# ── V1 in-scope solvers ──────────────────────────────────────────────────

V1_SOLVERS: frozenset[str] = frozenset({
    # Single-phase flow
    "SinglePhaseFVM",
    "SinglePhaseHybridFVM",
    # Single-phase reservoir (flow + wells)
    "SinglePhaseReservoir",
    "SinglePhaseWell",
    # Compositional multiphase flow (includes CO2-brine)
    "CompositionalMultiphaseFVM",
    "CompositionalMultiphaseHybridFVM",
    # Compositional reservoir (flow + wells)
    "CompositionalMultiphaseReservoir",
    "CompositionalMultiphaseWell",
    # Immiscible multiphase
    "ImmiscibleMultiphaseFlow",
})

# ── V1 in-scope constitutive models ──────────────────────────────────────

V1_CONSTITUTIVE: frozenset[str] = frozenset({
    # CO2-brine fluids
    "CO2BrineEzrokhiFluid",
    "CO2BrineEzrokhiThermalFluid",
    "CO2BrinePhillipsFluid",
    "CO2BrinePhillipsThermalFluid",
    # Other fluids
    "CompressibleSinglePhaseFluid",
    "BlackOilFluid",
    "DeadOilFluid",
    "CompositionalMultiphaseFluid",
    "CompositionalTwoPhaseFluid",
    "CompositionalTwoPhaseFluidLohrenzBrayClark",
    "CompositionalTwoPhaseFluidPhillipsBrine",
    "CompositionalTwoPhaseKValueFluidLohrenzBrayClark",
    "CompositionalTwoPhaseKValueFluidPhillipsBrine",
    "CompositionalThreePhaseFluidLohrenzBrayClark",
    "TwoPhaseImmiscibleFluid",
    "InvariantImmiscibleFluid",
    "ThermalCompressibleSinglePhaseFluid",
    "ReactiveBrine",
    "ReactiveBrineThermal",
    # Relative permeability
    "BrooksCoreyRelativePermeability",
    "BrooksCoreyBakerRelativePermeability",
    "BrooksCoreyStone2RelativePermeability",
    "VanGenuchtenBakerRelativePermeability",
    "VanGenuchtenStone2RelativePermeability",
    "TableRelativePermeability",
    "TableRelativePermeabilityHysteresis",
    # Capillary pressure
    "BrooksCoreyCapillaryPressure",
    "VanGenuchtenCapillaryPressure",
    "JFunctionCapillaryPressure",
    "TableCapillaryPressure",
    # Permeability
    "ConstantPermeability",
    "CarmanKozenyPermeability",
    "CompressibleSolidCarmanKozenyPermeability",
    "CompressibleSolidConstantPermeability",
    "CompressibleSolidExponentialDecayPermeability",
    "CompressibleSolidParallelPlatesPermeability",
    "CompressibleSolidPressurePermeability",
    "CompressibleSolidSlipDependentPermeability",
    "CompressibleSolidWillisRichardsPermeability",
    # Porosity
    "BiotPorosity",
    "PressurePorosity",
    "ProppantPorosity",
})

# ── Sections that need filtering ─────────────────────────────────────────

_SECTION_SCOPE: dict[str, frozenset[str]] = {
    "Solvers": V1_SOLVERS,
    "Constitutive": V1_CONSTITUTIVE,
}


def filter_elements_for_section(
    section_name: str,
    elements: list[SchemaElement],
) -> list[SchemaElement]:
    """Return only in-scope elements for the given section.

    Sections without a defined scope (Mesh, Events, etc.) return all elements
    unchanged.
    """
    allowed = _SECTION_SCOPE.get(section_name)
    if allowed is None:
        return elements
    return [e for e in elements if e.name in allowed]
