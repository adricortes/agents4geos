"""Tests for fluid & constitutive tools."""

from agents4geosx.tools.fluid_tools import (
    compute_gas_properties, compute_oil_properties, compute_brine_properties,
    generate_pvt_table, generate_rel_perm, generate_cap_pressure,
    recommend_fluid_model,
)


def test_compute_gas_properties():
    result = compute_gas_properties(
        pressure_Pa=1e7, temperature_K=373.0, specific_gravity=0.7,
    )
    assert 0.5 < result["z_factor"] < 1.2
    assert result["density_kg_m3"] > 0
    assert result["viscosity_Pa_s"] > 0
    # Metadata must document correlation provenance
    meta = result["metadata"]
    assert "Dranchuk" in meta["z_factor_method"]
    assert "pyResToolbox" in meta["z_factor_method"]
    assert "Piper, McCain & Corredor" in meta["critical_properties_method"]
    assert "Lee, Gonzalez & Eakin" in meta["viscosity_note"]
    assert "Z-factor" in meta["density_note"]
    assert "Z-factor" in meta["Bg_note"]
    assert "Numerical derivative" in meta["compressibility_note"]


def test_compute_oil_properties():
    result = compute_oil_properties(
        pressure_Pa=2e7, temperature_K=373.0, api=35.0,
        gas_sg=0.7, rsb_sm3_sm3=100.0,
    )
    assert result["pb_Pa"] > 0
    assert result["rs_sm3_sm3"] >= 0
    assert result["bo_m3_m3"] > 0
    assert result["density_kg_m3"] > 0
    assert result["viscosity_Pa_s"] > 0
    assert result["compressibility_1_Pa"] > 0
    # Metadata must document correlation provenance
    meta = result["metadata"]
    assert "Valko-McCain" in meta["bubble_point_method"]
    assert "pyResToolbox" in meta["bubble_point_method"]
    assert "Velarde, Blasingame & McCain" in meta["rs_method"]
    assert "Standing, Witte, McCain-Hill" in meta["density_method"]
    assert "McCain" in meta["bo_method"]
    assert "Beggs-Robinson" in meta["viscosity_note"]
    assert "Petrosky-Farshad" in meta["viscosity_note"]
    assert "Numerical derivative" in meta["compressibility_note"]


def test_compute_brine_properties():
    result = compute_brine_properties(
        pressure_Pa=3e7, temperature_K=350.0, salinity_wt_pct=5.0,
    )
    assert 900 < result["density_kg_m3"] < 1200
    assert result["viscosity_Pa_s"] > 0
    assert "Bw" in result
    assert "compressibility_undersaturated_1_Pa" in result
    assert "compressibility_saturated_1_Pa" in result
    assert "Rs_ch4_sm3_sm3" in result
    # Metadata must document correlation provenance
    meta = result["metadata"]
    assert "Spivey" in meta["correlation"]
    assert "pyResToolbox" in meta["correlation"]
    assert "IAPWS-IF97" in meta["density_note"]
    assert "Mao-Duan" in meta["viscosity_note"]
    assert meta["salinity_convention"] == "NaCl weight percent"
    assert meta["ch4_saturation"] == 0.0


def test_compute_brine_properties_with_ch4():
    result = compute_brine_properties(
        pressure_Pa=3e7, temperature_K=350.0, salinity_wt_pct=5.0,
        ch4_saturation=0.5,
    )
    assert result["Rs_ch4_sm3_sm3"] > 0
    assert result["metadata"]["ch4_saturation"] == 0.5


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
    assert "material_list" in result
    elem_types = [e["type"] for e in result["constitutive_elements"]]
    assert "CO2BrinePhillipsFluid" in elem_types
    assert "CompressibleSolidConstantPermeability" in elem_types
    assert "NullModel" in elem_types


def test_generate_pvt_table_gas():
    result = generate_pvt_table(
        fluid_type="gas", pressure_range_Pa=[1e6, 3e7],
        temperature_K=373.0, n_rows=5,
    )
    assert "rows" in result
    assert "metadata" in result
    assert len(result["rows"]) == 5
    assert "pressure_Pa" in result["rows"][0]
    assert "z_factor" in result["rows"][0]
    assert "metadata" not in result["rows"][0]  # metadata not duplicated per row
    assert "Dranchuk" in result["metadata"]["z_factor_method"]


def test_generate_pvt_table_water():
    result = generate_pvt_table(
        fluid_type="water", pressure_range_Pa=[1e6, 3e7],
        temperature_K=350.0, n_rows=5,
    )
    assert len(result["rows"]) == 5
    assert "density_kg_m3" in result["rows"][0]
    assert "Spivey" in result["metadata"]["correlation"]


def test_recommend_fluid_model_single_phase():
    result = recommend_fluid_model(description="single phase water flow")
    assert "SinglePhaseFVM" in result["solver"]
    assert "water" in result["material_list"]
    assert "rock" in result["material_list"]
    elem_types = [e["type"] for e in result["constitutive_elements"]]
    assert "CompressibleSinglePhaseFluid" in elem_types
    assert "CompressibleSolidConstantPermeability" in elem_types
