"""NL keyword → GEOS constitutive model mapping (decision tree).

GEOS requires a specific constitutive assembly pattern:
- A fluid model (referenced in materialList)
- A coupled solid (e.g., CompressibleSolidConstantPermeability) that bundles
  a null solid, porosity model, and permeability model (referenced in materialList)
- The sub-models (NullModel, PressurePorosity, ConstantPermeability) are defined
  in <Constitutive> but NOT referenced directly in materialList
- For multiphase: a relative permeability model (referenced in materialList)
"""

from __future__ import annotations


# Each entry defines the full constitutive assembly for a physics type.
# "material_list" = what goes in CellElementRegion materialList
# "constitutive_elements" = all elements to add to <Constitutive> section
FLUID_MODEL_MAP: list[dict] = [
    {
        "keywords": ["co2", "carbon", "sequestration", "ccs"],
        "solver": "CompositionalMultiphaseFVM",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "CO2BrinePhillipsFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ gas, water }",
                "componentNames": "{ co2, water }",
                "componentMolarWeight": "{ 44e-3, 18e-3 }",
                "phasePVTParaFiles": "{ pvtgas.txt, pvtliquid.txt }",
                "flashModelParaFile": "flashModel.txt",
            }},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
            }},
            {"type": "NullModel", "name": "nullSolid", "attrs": {}},
            {"type": "PressurePorosity", "name": "rockPorosity", "attrs": {
                "defaultReferencePorosity": "0.2",
                "referencePressure": "0.0",
                "compressibility": "1.0e-9",
            }},
            {"type": "ConstantPermeability", "name": "rockPerm", "attrs": {
                "permeabilityComponents": "{ 1.0e-13, 1.0e-13, 1.0e-13 }",
            }},
            {"type": "BrooksCoreyRelativePermeability", "name": "relperm", "attrs": {
                "phaseNames": "{ gas, water }",
                "phaseMinVolumeFraction": "{ 0.05, 0.2 }",
                "phaseRelPermExponent": "{ 2.0, 4.0 }",
                "phaseRelPermMaxValue": "{ 0.9, 1.0 }",
            }},
        ],
        "notes": "CO2 injection uses compositional framework with CO2-brine EOS. "
                 "The CO2BrinePhillipsFluid requires PVT parameter files.",
    },
    {
        "keywords": ["compositional", "multiphase", "multicomponent", "eos"],
        "solver": "CompositionalMultiphaseFVM",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "CompositionalMultiphaseFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ oil, gas }",
                "equationsOfState": "{ PR, PR }",
                "componentNames": "{ C1, C10 }",
                "componentCriticalPressure": "{ 46e5, 25.3e5 }",
                "componentCriticalTemperature": "{ 190.6, 622.0 }",
                "componentAcentricFactor": "{ 0.011, 0.443 }",
                "componentMolarWeight": "{ 16e-3, 134e-3 }",
                "componentVolumeShift": "{ 0, 0 }",
                "componentBinaryCoeff": "{ { 0, 0 }, { 0, 0 } }",
            }},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
            }},
            {"type": "NullModel", "name": "nullSolid", "attrs": {}},
            {"type": "PressurePorosity", "name": "rockPorosity", "attrs": {
                "defaultReferencePorosity": "0.2",
                "referencePressure": "0.0",
                "compressibility": "1.0e-9",
            }},
            {"type": "ConstantPermeability", "name": "rockPerm", "attrs": {
                "permeabilityComponents": "{ 1.0e-13, 1.0e-13, 1.0e-13 }",
            }},
            {"type": "BrooksCoreyRelativePermeability", "name": "relperm", "attrs": {
                "phaseNames": "{ oil, gas }",
                "phaseMinVolumeFraction": "{ 0.1, 0.15 }",
                "phaseRelPermExponent": "{ 2.0, 2.0 }",
                "phaseRelPermMaxValue": "{ 0.8, 0.9 }",
            }},
        ],
        "notes": "General compositional flow with Peng-Robinson EOS. "
                 "Adjust component properties for your specific fluid system.",
    },
    {
        "keywords": ["immiscible", "two-phase", "oil water", "water oil"],
        "solver": "ImmiscibleMultiphaseFlow",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "TwoPhaseImmiscibleFluid", "name": "fluid", "attrs": {}},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
            }},
            {"type": "NullModel", "name": "nullSolid", "attrs": {}},
            {"type": "PressurePorosity", "name": "rockPorosity", "attrs": {
                "defaultReferencePorosity": "0.2",
                "referencePressure": "0.0",
                "compressibility": "1.0e-9",
            }},
            {"type": "ConstantPermeability", "name": "rockPerm", "attrs": {
                "permeabilityComponents": "{ 1.0e-13, 1.0e-13, 1.0e-13 }",
            }},
            {"type": "BrooksCoreyRelativePermeability", "name": "relperm", "attrs": {
                "phaseNames": "{ oil, water }",
                "phaseMinVolumeFraction": "{ 0.1, 0.15 }",
                "phaseRelPermExponent": "{ 2.0, 3.0 }",
                "phaseRelPermMaxValue": "{ 0.8, 1.0 }",
            }},
        ],
        "notes": "Immiscible two-phase flow.",
    },
    {
        "keywords": ["single phase", "single-phase", "water", "brine", "incompressible"],
        "solver": "SinglePhaseFVM",
        "material_list": ["water", "rock"],
        "constitutive_elements": [
            {"type": "CompressibleSinglePhaseFluid", "name": "water", "attrs": {
                "defaultDensity": "1000",
                "defaultViscosity": "0.001",
                "referencePressure": "0.0",
                "compressibility": "5e-10",
                "viscosibility": "0.0",
            }},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
            }},
            {"type": "NullModel", "name": "nullSolid", "attrs": {}},
            {"type": "PressurePorosity", "name": "rockPorosity", "attrs": {
                "defaultReferencePorosity": "0.2",
                "referencePressure": "0.0",
                "compressibility": "1.0e-9",
            }},
            {"type": "ConstantPermeability", "name": "rockPerm", "attrs": {
                "permeabilityComponents": "{ 1.0e-12, 1.0e-12, 1.0e-15 }",
            }},
        ],
        "notes": "Single-phase flow. The coupled solid (CompressibleSolidConstantPermeability) "
                 "bundles NullModel + PressurePorosity + ConstantPermeability. "
                 "materialList references only the fluid and coupled solid names.",
    },
]


def recommend_model(description: str) -> dict:
    """Match a natural language description to GEOS solver + constitutive assembly.

    Returns:
        solver: Solver element type
        material_list: Names for CellElementRegion materialList
        constitutive_elements: Full list of elements to add to <Constitutive>
        notes: Explanation
    """
    desc_lower = description.lower()
    for entry in FLUID_MODEL_MAP:
        if any(kw in desc_lower for kw in entry["keywords"]):
            return {
                "solver": entry["solver"],
                "material_list": entry["material_list"],
                "constitutive_elements": entry["constitutive_elements"],
                "notes": entry["notes"],
            }
    # Default: single-phase
    default = FLUID_MODEL_MAP[-1]
    return {
        "solver": default["solver"],
        "material_list": default["material_list"],
        "constitutive_elements": default["constitutive_elements"],
        "notes": "Default: single-phase flow",
    }
