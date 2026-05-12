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
    # === CO2-brine variants (most specific first so keyword matcher reaches them) ===
    {
        # Schema-defined but no inputFile coverage; we still produce a syntactically
        # valid deck and let the orchestrator warn that no validated exemplar exists.
        "keywords": ["ezrokhi thermal", "thermal ezrokhi"],
        "solver": "CompositionalMultiphaseFVM",
        "solver_attrs": {"isThermal": "1"},
        "material_list": ["fluid", "rock", "relperm", "thermalCond"],
        "constitutive_elements": [
            {"type": "CO2BrineEzrokhiThermalFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ gas, water }",
                "componentNames": "{ co2, water }",
                "componentMolarWeight": "{ 44e-3, 18e-3 }",
                "phasePVTParaFiles": "{ pvtgas.txt, pvtliquid_ez.txt }",
                "flashModelParaFile": "co2flash.txt",
            }},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
                "solidInternalEnergyModelName": "rockInternalEnergy",
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
            {"type": "SolidInternalEnergy", "name": "rockInternalEnergy", "attrs": {
                "referenceVolumetricHeatCapacity": "1.95e6",
                "referenceTemperature": "368.15",
                "referenceInternalEnergy": "0",
            }},
            {"type": "BrooksCoreyRelativePermeability", "name": "relperm", "attrs": {
                "phaseNames": "{ gas, water }",
                "phaseMinVolumeFraction": "{ 0.05, 0.2 }",
                "phaseRelPermExponent": "{ 2.0, 4.0 }",
                "phaseRelPermMaxValue": "{ 0.9, 1.0 }",
            }},
            {"type": "MultiPhaseConstantThermalConductivity", "name": "thermalCond", "attrs": {
                "phaseNames": "{ gas, water }",
                "thermalConductivityComponents": "{ 0.6, 0.6, 0.6 }",
            }},
        ],
        "notes": "Thermal CO2-brine with Ezrokhi correlations. Schema-defined but "
                 "has ZERO inputFile coverage — no validated exemplar exists. Output "
                 "is structurally valid but downstream behavior is not benchmarked. "
                 "Prefer CO2BrinePhillipsThermalFluid (which has 4 inputFile uses) "
                 "unless the user specifically needs Ezrokhi salinity handling AND "
                 "thermal physics. See knowledge/examples/co2_brine.md.",
    },
    {
        "keywords": ["co2 thermal", "thermal co2", "non-isothermal co2",
                     "supercritical co2 thermal", "joule-thomson co2", "cold co2"],
        "solver": "CompositionalMultiphaseFVM",
        "solver_attrs": {"isThermal": "1"},
        "material_list": ["fluid", "rock", "relperm", "thermalCond"],
        "constitutive_elements": [
            {"type": "CO2BrinePhillipsThermalFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ gas, water }",
                "componentNames": "{ co2, water }",
                "componentMolarWeight": "{ 44e-3, 18e-3 }",
                "phasePVTParaFiles": "{ pvtgas.txt, pvtliquid.txt }",
                "flashModelParaFile": "co2flash.txt",
            }},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
                "solidInternalEnergyModelName": "rockInternalEnergy",
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
            {"type": "SolidInternalEnergy", "name": "rockInternalEnergy", "attrs": {
                "referenceVolumetricHeatCapacity": "1.95e6",
                "referenceTemperature": "368.15",
                "referenceInternalEnergy": "0",
            }},
            {"type": "BrooksCoreyRelativePermeability", "name": "relperm", "attrs": {
                "phaseNames": "{ gas, water }",
                "phaseMinVolumeFraction": "{ 0.0, 0.0 }",
                "phaseRelPermExponent": "{ 1.5, 1.5 }",
                "phaseRelPermMaxValue": "{ 0.9, 0.9 }",
            }},
            {"type": "MultiPhaseConstantThermalConductivity", "name": "thermalCond", "attrs": {
                "phaseNames": "{ gas, water }",
                "thermalConductivityComponents": "{ 0.6, 0.6, 0.6 }",
            }},
        ],
        "notes": "Thermal CO2-brine (Phillips). Use for J-T cooling at the wellhead, "
                 "cold-plume thermodynamics, or geothermal coupling. Requires "
                 "isThermal='1' on solver (and on any well solver — see "
                 "knowledge/examples/wells.md §F). Adds SolidInternalEnergy + "
                 "MultiPhaseConstantThermalConductivity to the thermal trio. "
                 "Consider adding ConstantDiffusion for phase-wise component diffusion.",
    },
    {
        "keywords": ["ezrokhi", "high salinity co2", "co2 ezrokhi", "salinity co2"],
        "solver": "CompositionalMultiphaseFVM",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "CO2BrineEzrokhiFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ gas, water }",
                "componentNames": "{ co2, water }",
                "componentMolarWeight": "{ 44e-3, 18e-3 }",
                "phasePVTParaFiles": "{ pvtgas.txt, pvtliquid_ez.txt }",
                "flashModelParaFile": "co2flash.txt",
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
        "notes": "CO2-brine with Ezrokhi correlations (better at high salinity than "
                 "Phillips). Same XML interface as CO2BrinePhillipsFluid but the "
                 "underlying brine density/viscosity parametrization differs. PVT "
                 "files typically use the '_ez' suffix. Only 4 inputFile uses (all "
                 "SPE Class 09 Pb3 benchmarks). See knowledge/examples/co2_brine.md.",
    },
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
        "keywords": ["black oil", "blackoil", "depletion drive", "oil with dissolved gas",
                     "saturated oil", "unsaturated oil"],
        "solver": "CompositionalMultiphaseFVM",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "BlackOilFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ oil, gas, water }",
                # Surface densities at standard conditions: oil ~800 kg/m^3 (light crude),
                # gas ~0.86 kg/m^3 (sales-gas equivalent), water ~1020 kg/m^3 (brine).
                "surfaceDensities": "{ 800.907131537, 0.856234902739, 1020.3440 }",
                "componentMolarWeight": "{ 120e-3, 25e-3, 18e-3 }",
                # PVTO = oil with dissolved gas (Rs vs P), PVTG = gas with no vaporized
                # oil (Bg, mu_g), PVTW = water. For unsaturated cases, swap to PVDO.
                "tableFiles": "{ pvto.txt, pvtg.txt, pvtw.txt }",
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
                "phaseNames": "{ oil, gas, water }",
                "phaseMinVolumeFraction": "{ 0.1, 0.05, 0.15 }",
                "phaseRelPermExponent": "{ 2.0, 2.0, 2.0 }",
                "phaseRelPermMaxValue": "{ 0.8, 0.9, 0.9 }",
            }},
        ],
        "notes": "Black oil (oil + dissolved/free gas + water) — 3-phase with PVT-table "
                 "mass transfer (Rs/Rv). Component order is {oil, gas, water} by convention. "
                 "Saturated variant (free gas, Rs = Rs_max) uses PVTO/PVTG tables; "
                 "unsaturated (all gas dissolved, Rs < Rs_max) uses PVDO/PVDG instead. "
                 "3-phase Brooks-Corey defaults to Stone-I interpolation — swap to "
                 "BrooksCoreyStone2RelativePermeability for Stone-II (intermediate-wet "
                 "oil-gas-water systems). See knowledge/examples/black_oil.md.",
    },
    {
        "keywords": ["dead oil", "deadoil", "oil water no gas"],
        "solver": "CompositionalMultiphaseFVM",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "DeadOilFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ oil, gas, water }",
                "surfaceDensities": "{ 800.0, 0.9907, 1022.0 }",
                "componentMolarWeight": "{ 114e-3, 16e-3, 18e-3 }",
                "tableFiles": "{ pvdo.txt, pvdg.txt, pvtw.txt }",
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
                "phaseNames": "{ oil, gas, water }",
                "phaseMinVolumeFraction": "{ 0.1, 0.15, 0.15 }",
                "phaseRelPermExponent": "{ 2.0, 2.0, 2.0 }",
                "phaseRelPermMaxValue": "{ 0.8, 0.9, 0.9 }",
            }},
        ],
        "notes": "Dead oil — 2- or 3-phase immiscible no-mass-transfer container. Despite "
                 "the name, also used to model gas-water systems (e.g. Buckley-Leverett "
                 "uses DeadOilFluid for CO2-water with componentMolarWeight={44, 18}). "
                 "Requires external PVT table files. Phase count is set by phaseNames "
                 "and MUST match the lengths of surfaceDensities, componentMolarWeight, "
                 "and tableFiles. See knowledge/examples/dead_oil.md.",
    },
    {
        "keywords": ["thermal", "heat", "temperature dependent", "geothermal"],
        "solver": "SinglePhaseFVM",
        "solver_attrs": {"isThermal": "1"},
        "material_list": ["fluid", "rock", "thermalCond"],
        "constitutive_elements": [
            {"type": "ThermalCompressibleSinglePhaseFluid", "name": "fluid", "attrs": {
                "defaultDensity": "1000",
                "defaultViscosity": "1e-4",
                "referencePressure": "0.0",
                "referenceTemperature": "273.0",
                "compressibility": "5e-10",
                "thermalExpansionCoeff": "3e-4",
                "viscosibility": "0.0",
                "specificHeatCapacity": "4.0e3",
                "referenceInternalEnergy": "1.1e6",
            }},
            {"type": "CompressibleSolidConstantPermeability", "name": "rock", "attrs": {
                "solidModelName": "nullSolid",
                "porosityModelName": "rockPorosity",
                "permeabilityModelName": "rockPerm",
                "solidInternalEnergyModelName": "rockInternalEnergy",
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
            {"type": "SolidInternalEnergy", "name": "rockInternalEnergy", "attrs": {
                "referenceVolumetricHeatCapacity": "1.95e6",
                "referenceTemperature": "273.0",
                "referenceInternalEnergy": "5.33e8",
            }},
            {"type": "SinglePhaseThermalConductivity", "name": "thermalCond", "attrs": {
                "defaultThermalConductivityComponents": "{ 1.66, 1.66, 1.66 }",
                "thermalConductivityGradientComponents": "{ 0, 0, 0 }",
                "referenceTemperature": "0",
            }},
        ],
        "notes": "Thermal single-phase flow. Requires isThermal='1' on solver, "
                 "ThermalCompressibleSinglePhaseFluid, SolidInternalEnergy, and "
                 "SinglePhaseThermalConductivity. Coupled solid gets solidInternalEnergyModelName.",
    },
    {
        "keywords": ["immiscible", "two-phase immiscible", "two-phase oil water",
                     "oil water no transfer", "spe10 immiscible"],
        # NOTE: ImmiscibleMultiphaseFlow is not actually a v0.1 solver — production decks
        # use CompositionalMultiphaseFVM with TwoPhaseImmiscibleFluid (e.g. the SPE 10
        # layer 84 and Buckley-Leverett immiscible benchmarks). Keep the solver field
        # in sync with how the orchestrator actually wires the deck.
        "solver": "CompositionalMultiphaseFVM",
        "material_list": ["fluid", "rock", "relperm"],
        "constitutive_elements": [
            {"type": "TwoPhaseImmiscibleFluid", "name": "fluid", "attrs": {
                "phaseNames": "{ oil, water }",
                # densityTableNames + viscosityTableNames reference <TableFunction>
                # elements declared under <Functions>. Each table must provide P vs
                # density (kg/m^3) and P vs viscosity (Pa·s) for its phase.
                "densityTableNames": "{ densityTableOil, densityTableWater }",
                "viscosityTableNames": "{ viscosityTableOil, viscosityTableWater }",
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
