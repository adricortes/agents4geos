"""Tests for the fluid_models knowledge module.

Verifies the keyword→recipe routing and structural shape of every entry
in FLUID_MODEL_MAP. Acceptance for agents4geos-fot: every new fluid
family (BlackOilFluid, CO2BrineEzrokhi[Thermal]Fluid, CO2BrinePhillipsThermalFluid,
filled-in TwoPhaseImmiscibleFluid) is reachable via a distinct keyword
and produces a recipe whose required attributes are present.
"""
from __future__ import annotations

import pytest

from agents4geos.knowledge.fluid_models import FLUID_MODEL_MAP, recommend_model


# Required-attr expectations per element type, sourced from the GEOS schema
# (parsed via agents4geos.config.get_schema). Only the attributes the schema
# marks required (or that the orchestrator must always set even if optional)
# are listed — defaults are fine for everything else.
REQUIRED_ATTRS_BY_TYPE: dict[str, set[str]] = {
    "BlackOilFluid": {"phaseNames", "componentMolarWeight", "surfaceDensities"},
    "DeadOilFluid": {"phaseNames"},
    "CO2BrinePhillipsFluid": {"phasePVTParaFiles"},
    "CO2BrineEzrokhiFluid": {"phasePVTParaFiles"},
    "CO2BrinePhillipsThermalFluid": {"phasePVTParaFiles"},
    "CO2BrineEzrokhiThermalFluid": {"phasePVTParaFiles"},
    "CompositionalMultiphaseFluid": {"phaseNames", "equationsOfState", "componentNames"},
    "CompressibleSinglePhaseFluid": set(),
    "ThermalCompressibleSinglePhaseFluid": set(),
    "TwoPhaseImmiscibleFluid": {"phaseNames"},
}

# Expected GEOS solver per fluid family. The pairing is fixed by which solver
# implements which physics: ImmiscibleMultiphaseFlow accepts only
# TwoPhaseImmiscibleFluid; SinglePhaseFVM accepts the single-phase fluids;
# CompositionalMultiphaseFVM handles everything else.
EXPECTED_SOLVER_BY_FLUID: dict[str, str] = {
    "BlackOilFluid": "CompositionalMultiphaseFVM",
    "DeadOilFluid": "CompositionalMultiphaseFVM",
    "CO2BrinePhillipsFluid": "CompositionalMultiphaseFVM",
    "CO2BrineEzrokhiFluid": "CompositionalMultiphaseFVM",
    "CO2BrinePhillipsThermalFluid": "CompositionalMultiphaseFVM",
    "CO2BrineEzrokhiThermalFluid": "CompositionalMultiphaseFVM",
    "CompositionalMultiphaseFluid": "CompositionalMultiphaseFVM",
    "TwoPhaseImmiscibleFluid": "ImmiscibleMultiphaseFlow",
    "CompressibleSinglePhaseFluid": "SinglePhaseFVM",
    "ThermalCompressibleSinglePhaseFluid": "SinglePhaseFVM",
}


_KNOWN_FLUID_TYPES = set(REQUIRED_ATTRS_BY_TYPE.keys())


def _fluid_element(recipe: dict) -> dict:
    """Return the first constitutive element whose type is a known fluid model.

    Element naming is not uniform across recipes — single-phase uses name='water'
    while multiphase uses name='fluid'. Routing by type is more robust.
    """
    for el in recipe["constitutive_elements"]:
        if el["type"] in _KNOWN_FLUID_TYPES:
            return el
    raise AssertionError(
        f"recipe has no element whose type is a known fluid model. "
        f"Element types present: {[el['type'] for el in recipe['constitutive_elements']]}"
    )


@pytest.mark.parametrize("entry", FLUID_MODEL_MAP)
def test_every_entry_has_a_fluid_element(entry):
    """Every recipe must have a constitutive element of a known fluid type."""
    has_fluid = any(el["type"] in _KNOWN_FLUID_TYPES
                    for el in entry["constitutive_elements"])
    assert has_fluid, f"entry with keywords {entry['keywords']!r} has no fluid element"


@pytest.mark.parametrize("entry", FLUID_MODEL_MAP)
def test_every_entry_has_a_known_fluid_type(entry):
    """The fluid element type must be one we have schema knowledge of."""
    fluid = _fluid_element(entry)
    assert fluid["type"] in REQUIRED_ATTRS_BY_TYPE, (
        f"fluid type {fluid['type']!r} not in REQUIRED_ATTRS_BY_TYPE — either add "
        f"it to the test or the entry uses an unknown element"
    )


@pytest.mark.parametrize("entry", FLUID_MODEL_MAP)
def test_solver_matches_fluid_family(entry):
    """Each entry's solver must be the canonical solver for its fluid type.

    Regression: prior to this test, the immiscible entry's solver was set to
    CompositionalMultiphaseFVM (incorrect) without any test catching it.
    """
    fluid = _fluid_element(entry)
    expected = EXPECTED_SOLVER_BY_FLUID[fluid["type"]]
    assert entry["solver"] == expected, (
        f"fluid {fluid['type']!r} (entry keywords {entry['keywords']!r}) "
        f"declares solver {entry['solver']!r} but the canonical solver for this "
        f"family is {expected!r}"
    )


@pytest.mark.parametrize("entry", FLUID_MODEL_MAP)
def test_required_attrs_present(entry):
    """Every required attr for the fluid element type must appear in attrs."""
    fluid = _fluid_element(entry)
    required = REQUIRED_ATTRS_BY_TYPE[fluid["type"]]
    missing = required - set(fluid["attrs"])
    assert not missing, (
        f"{fluid['type']} (entry keywords {entry['keywords']!r}) is missing required "
        f"attrs: {sorted(missing)}"
    )


# --- routing tests: each NEW fluid family is reachable via its distinctive keyword ---

@pytest.mark.parametrize("query,expected_type", [
    ("CO2 storage in a brine aquifer", "CO2BrinePhillipsFluid"),
    ("co2 sequestration", "CO2BrinePhillipsFluid"),
    ("co2 ezrokhi with high salinity brine", "CO2BrineEzrokhiFluid"),
    ("ezrokhi correlation", "CO2BrineEzrokhiFluid"),
    ("thermal co2 storage with Joule-Thomson cooling", "CO2BrinePhillipsThermalFluid"),
    ("co2 thermal", "CO2BrinePhillipsThermalFluid"),
    ("non-isothermal co2 injection", "CO2BrinePhillipsThermalFluid"),
    ("ezrokhi thermal CO2", "CO2BrineEzrokhiThermalFluid"),
    ("black oil waterflood", "BlackOilFluid"),
    ("blackoil depletion drive", "BlackOilFluid"),
    ("dead oil two-phase", "DeadOilFluid"),
    ("immiscible two-phase oil water", "TwoPhaseImmiscibleFluid"),
    ("spe10 immiscible benchmark", "TwoPhaseImmiscibleFluid"),
    ("thermal flow with heat transport", "ThermalCompressibleSinglePhaseFluid"),
    ("compositional multiphase with PR EOS", "CompositionalMultiphaseFluid"),
    ("single phase water flow", "CompressibleSinglePhaseFluid"),
])
def test_routing(query, expected_type):
    """Distinctive keywords route to the intended fluid family.

    Ordering of FLUID_MODEL_MAP matters: more-specific entries must precede
    less-specific ones so the first-match-wins keyword scan reaches them.
    """
    recipe = recommend_model(query)
    fluid_types = [el["type"] for el in recipe["constitutive_elements"]
                   if el["type"] in _KNOWN_FLUID_TYPES]
    assert expected_type in fluid_types, (
        f"query {query!r} returned fluid {fluid_types!r}, expected {expected_type!r}. "
        f"recipe notes: {recipe.get('notes', '')[:80]}"
    )


def test_thermal_co2_carries_isThermal_flag():
    """Thermal CO2 variants must set isThermal='1' on the solver."""
    for query, expected in [
        ("co2 thermal", "CO2BrinePhillipsThermalFluid"),
        ("ezrokhi thermal co2", "CO2BrineEzrokhiThermalFluid"),
    ]:
        recipe = recommend_model(query)
        # The recipe entry's solver_attrs must contain isThermal='1' — look it up
        # by scanning FLUID_MODEL_MAP for the matching fluid type.
        matching = [e for e in FLUID_MODEL_MAP
                    if any(el["type"] == expected for el in e["constitutive_elements"])]
        assert matching, f"no FLUID_MODEL_MAP entry uses {expected}"
        entry = matching[0]
        assert entry.get("solver_attrs", {}).get("isThermal") == "1", (
            f"thermal CO2 entry for {expected} missing isThermal='1' on solver"
        )


def test_thermal_co2_carries_thermal_constitutive_trio():
    """Thermal CO2 needs SolidInternalEnergy + MultiPhaseConstantThermalConductivity
    plus solidInternalEnergyModelName on the coupled solid."""
    for query, expected in [
        ("co2 thermal", "CO2BrinePhillipsThermalFluid"),
        ("ezrokhi thermal", "CO2BrineEzrokhiThermalFluid"),
    ]:
        recipe = recommend_model(query)
        types = {el["type"] for el in recipe["constitutive_elements"]}
        assert "SolidInternalEnergy" in types, (
            f"{expected} recipe missing SolidInternalEnergy"
        )
        assert "MultiPhaseConstantThermalConductivity" in types, (
            f"{expected} recipe missing MultiPhaseConstantThermalConductivity"
        )
        # Coupled solid must carry solidInternalEnergyModelName
        coupled = next((el for el in recipe["constitutive_elements"]
                        if el["type"] == "CompressibleSolidConstantPermeability"), None)
        assert coupled is not None, f"{expected} recipe missing coupled solid"
        assert "solidInternalEnergyModelName" in coupled["attrs"], (
            f"{expected} coupled solid missing solidInternalEnergyModelName wiring"
        )


def test_blackoil_distinct_from_deadoil():
    """The 'black oil' keyword must route to BlackOilFluid, not DeadOilFluid.

    Regression: prior to agents4geos-fot the two were conflated in one entry.
    """
    bo = recommend_model("black oil simulation")
    do = recommend_model("dead oil simulation")
    assert _fluid_element(bo)["type"] == "BlackOilFluid"
    assert _fluid_element(do)["type"] == "DeadOilFluid"


def test_immiscible_has_table_references():
    """TwoPhaseImmiscibleFluid recipe must reference density and viscosity tables.

    Prior to agents4geos-fot the entry had empty attrs — unblocks the
    immiscible category in the example catalog.
    """
    recipe = recommend_model("immiscible two-phase oil water")
    fluid = _fluid_element(recipe)
    assert fluid["type"] == "TwoPhaseImmiscibleFluid"
    assert "densityTableNames" in fluid["attrs"]
    assert "viscosityTableNames" in fluid["attrs"]


def test_fallback_for_unknown_returns_single_phase():
    """An unmatched description falls back to single-phase (the safe default)."""
    recipe = recommend_model("some completely unrelated description")
    fluid = _fluid_element(recipe)
    assert fluid["type"] == "CompressibleSinglePhaseFluid"
