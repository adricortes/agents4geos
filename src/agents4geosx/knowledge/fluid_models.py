"""NL keyword → GEOS constitutive model mapping (decision tree)."""

from __future__ import annotations

FLUID_MODEL_MAP: list[dict] = [
    {
        "keywords": ["co2", "carbon", "sequestration", "ccs"],
        "solver": "CompositionalMultiphaseFVM",
        "constitutive_models": ["CO2BrinePhillipsFluid", "BrooksCoreyRelativePermeability", "ConstantPermeability", "BiotPorosity"],
        "notes": "CO2 injection uses compositional framework with CO2-brine EOS",
    },
    {
        "keywords": ["compositional", "multiphase", "multicomponent", "eos"],
        "solver": "CompositionalMultiphaseFVM",
        "constitutive_models": ["CompositionalMultiphaseFluid", "BrooksCoreyRelativePermeability", "ConstantPermeability"],
        "notes": "General compositional flow with Peng-Robinson EOS",
    },
    {
        "keywords": ["black oil", "dead oil", "blackoil"],
        "solver": "CompositionalMultiphaseFVM",
        "constitutive_models": ["BlackOilFluid", "BrooksCoreyRelativePermeability", "ConstantPermeability"],
        "notes": "Black oil model",
    },
    {
        "keywords": ["immiscible", "two-phase", "oil water", "water oil"],
        "solver": "ImmiscibleMultiphaseFlow",
        "constitutive_models": ["TwoPhaseImmiscibleFluid", "BrooksCoreyRelativePermeability", "ConstantPermeability"],
        "notes": "Immiscible two-phase flow",
    },
    {
        "keywords": ["single phase", "single-phase", "water", "brine", "incompressible"],
        "solver": "SinglePhaseFVM",
        "constitutive_models": ["CompressibleSinglePhaseFluid", "ConstantPermeability", "PressurePorosity"],
        "notes": "Single-phase flow",
    },
]


def recommend_model(description: str) -> dict:
    """Match a natural language description to GEOS solver + constitutive models."""
    desc_lower = description.lower()
    for entry in FLUID_MODEL_MAP:
        if any(kw in desc_lower for kw in entry["keywords"]):
            return {
                "solver": entry["solver"],
                "constitutive_models": entry["constitutive_models"],
                "notes": entry["notes"],
            }
    return {
        "solver": "SinglePhaseFVM",
        "constitutive_models": ["CompressibleSinglePhaseFluid", "ConstantPermeability", "PressurePorosity"],
        "notes": "Default: single-phase",
    }
