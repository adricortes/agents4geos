"""Tests for fluid & constitutive tools."""

from agents4geosx.tools.fluid_tools import (
    compute_gas_properties, compute_brine_properties,
    generate_rel_perm, generate_cap_pressure, recommend_fluid_model,
)


def test_compute_gas_properties():
    result = compute_gas_properties(
        pressure_Pa=1e7, temperature_K=373.0, specific_gravity=0.7,
    )
    assert 0.5 < result["z_factor"] < 1.2
    assert result["density_kg_m3"] > 0
    assert result["viscosity_Pa_s"] > 0


def test_compute_brine_properties():
    result = compute_brine_properties(
        pressure_Pa=3e7, temperature_K=350.0, salinity_wt_pct=5.0,
    )
    assert 900 < result["density_kg_m3"] < 1200
    assert result["viscosity_Pa_s"] > 0


def test_generate_rel_perm_brooks_corey():
    result = generate_rel_perm(
        model="BrooksCorey", swc=0.15, sorg=0.1,
        exponents={"nw": 3.0, "no": 2.0}, n_rows=25,
    )
    assert len(result) == 25
    assert "Sw" in result[0]
    assert "Krw" in result[0]
    assert "Kro" in result[0]


def test_generate_cap_pressure():
    result = generate_cap_pressure(
        model="BrooksCorey", entry_pressure_Pa=1e4,
        swc=0.15, exponent=2.0, n_rows=20,
    )
    assert len(result) == 20
    assert "Sw" in result[0]
    assert "Pc_Pa" in result[0]


def test_recommend_fluid_model_co2():
    result = recommend_fluid_model(description="CO2 injection into saline aquifer")
    assert "CompositionalMultiphaseFVM" in result["solver"]
    assert any("CO2" in m for m in result["constitutive_models"])


def test_recommend_fluid_model_single_phase():
    result = recommend_fluid_model(description="single phase water flow")
    assert "SinglePhaseFVM" in result["solver"]
