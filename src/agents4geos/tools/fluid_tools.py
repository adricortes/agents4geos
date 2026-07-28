"""Fluid & constitutive MCP tools (Group 2) — wraps pyResToolbox with SI units."""

from __future__ import annotations

import numpy as np

from agents4geos.server import mcp
from agents4geos.knowledge.fluid_models import recommend_model


@mcp.tool
def compute_gas_properties(
    pressure_Pa: float,
    temperature_K: float,
    specific_gravity: float,
    co2: float = 0.0,
    h2s: float = 0.0,
    n2: float = 0.0,
) -> dict:
    """Compute gas PVT properties at given conditions (all SI units).

    Args:
        pressure_Pa: Pressure in Pascals.
        temperature_K: Temperature in Kelvin.
        specific_gravity: Gas specific gravity relative to air.
        co2: Molar fraction of CO2 (0-1).
        h2s: Molar fraction of H2S (0-1).
        n2: Molar fraction of N2 (0-1).
    """
    from agents4geos.fluids import si_adapter as gas

    z = gas.gas_z(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                  co2=co2, h2s=h2s, n2=n2)
    rho = gas.gas_den(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                      co2=co2, h2s=h2s, n2=n2)
    mu = gas.gas_ug(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                    co2=co2, h2s=h2s, n2=n2)
    bg = gas.gas_bg(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                    co2=co2, h2s=h2s, n2=n2)
    cg = gas.gas_cg(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                    co2=co2, h2s=h2s, n2=n2)
    return {
        "z_factor": float(z),
        "density_kg_m3": float(rho),
        "viscosity_Pa_s": float(mu),
        "Bg_m3_m3": float(bg),
        "compressibility_1_Pa": float(cg),
        "metadata": {
            "z_factor_method": "DAK — Dranchuk & Abou-Kassem (1975), "
                               "Eqs 2.7-2.8 from McCain et al. "
                               "(pyResToolbox.gas.gas_z)",
            "critical_properties_method": "PMC — Piper, McCain & Corredor (1999), "
                                          "Eqs 2.4-2.6 from McCain et al. "
                                          "(pyResToolbox.gas.gas_z)",
            "viscosity_note": "Lee, Gonzalez & Eakin (1966), "
                              "Eqs 2.14-2.17 from McCain et al. "
                              "(pyResToolbox.gas.gas_ug)",
            "density_note": "Derived from Z-factor via real gas law "
                            "(pyResToolbox.gas.gas_den)",
            "Bg_note": "Derived from Z-factor "
                       "(pyResToolbox.gas.gas_bg)",
            "compressibility_note": "Numerical derivative of Z-factor "
                                    "(pyResToolbox.gas.gas_cg)",
        },
    }


@mcp.tool
def compute_oil_properties(
    pressure_Pa: float,
    temperature_K: float,
    api: float,
    gas_sg: float,
    rsb_sm3_sm3: float,
) -> dict:
    """Compute oil PVT properties at given conditions (all SI units).

    Args:
        pressure_Pa: Pressure in Pascals.
        temperature_K: Temperature in Kelvin.
        api: Stock tank oil density in degrees API.
        gas_sg: Weighted average specific gravity of surface gas (relative to air).
        rsb_sm3_sm3: Oil solution gas volume at bubble point (sm3/sm3).
    """
    from agents4geos.fluids import si_adapter as oil

    sg_o = 141.5 / (131.5 + api)
    pb = oil.oil_pbub(api=api, degf=temperature_K, rsb=rsb_sm3_sm3,
                      sg_g=gas_sg)
    rs = oil.oil_rs(p=pressure_Pa, pb=pb, api=api, degf=temperature_K,
                    rsb=rsb_sm3_sm3, sg_sp=gas_sg)
    bo = oil.oil_bo(p=pressure_Pa, pb=pb, degf=temperature_K,
                    rs=rs, rsb=rsb_sm3_sm3, sg_o=sg_o,
                    sg_g=gas_sg)
    rho = oil.oil_deno(p=pressure_Pa, degf=temperature_K, rs=rs,
                       rsb=rsb_sm3_sm3, sg_g=gas_sg, pb=pb,
                       api=api)
    mu = oil.oil_viso(p=pressure_Pa, api=api, degf=temperature_K,
                      pb=pb, rs=rs)
    co = oil.oil_co(p=pressure_Pa, api=api, degf=temperature_K,
                    sg_g=gas_sg, pb=pb, rsb=rsb_sm3_sm3)
    return {
        "pb_Pa": float(pb),
        "rs_sm3_sm3": float(rs),
        "bo_m3_m3": float(bo),
        "density_kg_m3": float(rho),
        "viscosity_Pa_s": float(mu),
        "compressibility_1_Pa": float(co),
        "metadata": {
            "bubble_point_method": "VALMC — Valko-McCain (2003) "
                                   "(pyResToolbox.oil.oil_pbub)",
            "rs_method": "VELAR — Velarde, Blasingame & McCain (1997) "
                         "(pyResToolbox.oil.oil_rs)",
            "density_method": "SWMH — Standing, Witte, McCain-Hill (1995) "
                              "(pyResToolbox.oil.oil_deno)",
            "bo_method": "MCAIN — McCain approach from densities "
                         "(pyResToolbox.oil.oil_bo)",
            "viscosity_note": "Beggs-Robinson (1975) at saturated pressures, "
                              "Petrosky-Farshad (1995) at undersaturated pressures "
                              "(pyResToolbox.oil.oil_viso)",
            "compressibility_note": "EXPLT — Numerical derivative of Bo "
                                    "(pyResToolbox.oil.oil_co)",
        },
    }


@mcp.tool
def compute_brine_properties(
    pressure_Pa: float,
    temperature_K: float,
    salinity_wt_pct: float = 0.0,
    ch4_saturation: float = 0.0,
) -> dict:
    """Compute water/brine PVT properties (all SI units).

    Args:
        pressure_Pa: Pressure in Pascals.
        temperature_K: Temperature in Kelvin.
        salinity_wt_pct: NaCl salt weight percent (0-100).
        ch4_saturation: Degree of methane saturation (0-1). 0 = no dissolved CH4,
                        1 = fully saturated at given P/T.
    """
    from agents4geos.fluids import si_adapter as brine

    result = brine.brine_props(p=pressure_Pa, degf=temperature_K,
                               wt=salinity_wt_pct, ch4_sat=ch4_saturation)
    # brine_props SI returns: (Bw, density_kg_m3, viscosity_Pa_s, [cw_usat, cw_sat], Rs_ch4)
    cw_list = result[3]
    cw_usat = float(cw_list[0]) if isinstance(cw_list, list) and len(cw_list) > 0 else 0.0
    cw_sat = float(cw_list[1]) if isinstance(cw_list, list) and len(cw_list) > 1 else cw_usat

    return {
        "density_kg_m3": float(result[1]),
        "viscosity_Pa_s": float(result[2]),
        "Bw": float(result[0]),
        "compressibility_undersaturated_1_Pa": cw_usat,
        "compressibility_saturated_1_Pa": cw_sat,
        "Rs_ch4_sm3_sm3": float(result[4]),
        "metadata": {
            "correlation": "Modified Spivey Correlation per McCain, "
                           "Petroleum Reservoir Fluid Properties pg 160 "
                           "(pyResToolbox.brine.brine_props)",
            "density_note": "IAPWS-IF97 freshwater density with Spivey NaCl correction",
            "viscosity_note": "Mao-Duan (2009) relative viscosity "
                              "(pyResToolbox source comment, line 456)",
            "salinity_convention": "NaCl weight percent",
            "reference_state_Bw": "15 degC, 0.1013 MPa",
            "ch4_saturation": ch4_saturation,
        },
    }


@mcp.tool
def compute_co2_brine_properties(
    pressure_Pa: float,
    temperature_K: float,
    salinity_wt_pct: float = 0.0,
    include_saturated_compressibility: bool = True,
) -> dict:
    """Compute CO2-saturated brine properties and CO2/brine mutual solubility (all SI units).

    Uses the Spycher-Pruess (2010) phase-partitioning model for CO2-brine mutual
    solubility, with Garcia (2001) dissolved-CO2 density correction, Spivey brine
    density on IAPWS-IF97 freshwater, Mao-Duan (2009) brine viscosity, and
    Islam-Carlson (2012) dissolved-CO2 viscosity correction. Intended for CO2
    storage / sequestration conditions (QC and reporting alongside the
    CO2BrinePhillipsFluid / CO2BrineEzrokhiFluid deck path; GEOS computes its
    own PVT internally from phasePVTParaFiles).

    Args:
        pressure_Pa: Pressure in Pascals.
        temperature_K: Temperature in Kelvin.
        salinity_wt_pct: NaCl-equivalent salinity, weight percent (0-100).
        include_saturated_compressibility: If True, also compute the saturated
            brine compressibility (Cf_sat); roughly doubles the calculation.
    """
    from agents4geos.fluids import si_adapter as brine

    ppm = salinity_wt_pct * 1.0e4  # wt% -> NaCl ppm (1 wt% = 10,000 ppm)
    mix = brine.CO2_Brine_Mixture(
        pres=pressure_Pa,
        temp=temperature_K,
        ppm=ppm,
        cw_sat=include_saturated_compressibility,
    )

    # In SI mode the library returns bDen [kg/m3], bVis [Pa.s], Cf_* [1/Pa],
    # Rs [sm3/sm3], bw [m3/m3 ratio]. bDen/bVis/bw are 3-lists indexed
    # [CO2-saturated, CO2-free brine, pure water]. With salt, x sums to
    # 1 - xSalt, so xCO2 + xH2O < 1 by design.
    warnings: list[str] = []
    if ppm > mix.ppm_sat:
        warnings.append(
            f"Requested salinity {ppm:.0f} ppm exceeds the maximum soluble salt "
            f"at this temperature ({mix.ppm_sat:.0f} ppm, Whitson Eq 9.1); "
            f"results are extrapolated."
        )
    temp_C = temperature_K - 273.15
    if not 12.0 <= temp_C <= 300.0:
        warnings.append(
            f"Temperature {temp_C:.1f} degC is outside the Spycher-Pruess "
            f"calibration range (~12-300 degC)."
        )
    if pressure_Pa > 600e5:
        warnings.append(
            f"Pressure {pressure_Pa / 1e5:.0f} bar is above the ~600 bar "
            f"Spycher-Pruess calibration range."
        )

    result = {
        "xCO2": float(mix.x[0]),
        "xH2O": float(mix.x[1]),
        "yCO2": float(mix.y[0]),
        "yH2O": float(mix.y[1]),
        "co2_saturated_brine_density_kg_m3": float(mix.bDen[0]),
        "co2_free_brine_density_kg_m3": float(mix.bDen[1]),
        "co2_saturated_brine_viscosity_Pa_s": float(mix.bVis[0]),
        "Bw_co2_saturated_m3_m3": float(mix.bw[0]),
        "Rs_co2_sm3_sm3": float(mix.Rs),
        "compressibility_undersaturated_1_Pa": float(mix.Cf_usat),
        "max_salinity_ppm_at_T": float(mix.ppm_sat),
        "warnings": warnings,
        "metadata": {
            "solubility_method": "Spycher & Pruess (2010), Transp Porous Med 82:173-196 "
                                 "(pyResToolbox.brine.CO2_Brine_Mixture)",
            "brine_density_method": "Spivey NaCl correction on IAPWS-IF97 freshwater with "
                                    "Garcia (2001) dissolved-CO2 volume correction "
                                    "(pyResToolbox.brine.brine_props_co2)",
            "brine_viscosity_method": "Mao-Duan (2009) with Islam-Carlson (2012) dissolved-CO2 "
                                      "correction (pyResToolbox.brine.brine_props_co2)",
            "Rs_convention": "sm3 dissolved CO2 / sm3 brine; standard-condition residual Rs "
                             "subtracted (Burgoyne 2023 offset)",
            "salinity_convention": "NaCl-equivalent weight percent, converted to ppm internally",
            "valid_range_note": "Spycher-Pruess calibrated ~12-300 degC and to ~600 bar; "
                                "salinity must stay below max_salinity_ppm_at_T",
        },
    }
    if include_saturated_compressibility and mix.Cf_sat is not None:
        result["compressibility_saturated_1_Pa"] = float(mix.Cf_sat)
    return result


@mcp.tool
def generate_pvt_table(
    fluid_type: str,
    pressure_range_Pa: list[float],
    temperature_K: float,
    n_rows: int = 50,
    gas_specific_gravity: float = 0.7,
    co2: float = 0.0,
    h2s: float = 0.0,
    n2: float = 0.0,
    api: float | None = None,
    gas_sg: float | None = None,
    rsb_sm3_sm3: float | None = None,
) -> dict:
    """Generate a PVT table over a pressure range (all SI units).

    fluid_type "gas" uses gas_specific_gravity and the co2/h2s/n2 molar
    fractions; "oil" requires api, gas_sg and rsb_sm3_sm3; "water" uses
    pure-water defaults. Returns a dict with "rows" (list of property dicts
    per pressure) and "metadata" (correlation provenance, reported once for
    the whole table).
    """
    if fluid_type == "oil":
        missing = [name for name, value in (("api", api), ("gas_sg", gas_sg),
                                            ("rsb_sm3_sm3", rsb_sm3_sm3)) if value is None]
        if missing:
            return {"error": f"fluid_type='oil' requires: {', '.join(missing)}"}
    elif fluid_type not in ("gas", "water"):
        return {"error": f"Unsupported fluid_type '{fluid_type}'. Supported: gas, oil, water."}

    pressures = np.linspace(pressure_range_Pa[0], pressure_range_Pa[1], n_rows)
    rows = []
    metadata: dict = {}
    for p in pressures:
        pf = float(p)
        if fluid_type == "gas":
            result = compute_gas_properties(
                pressure_Pa=pf, temperature_K=temperature_K,
                specific_gravity=gas_specific_gravity, co2=co2, h2s=h2s, n2=n2)
        elif fluid_type == "oil":
            result = compute_oil_properties(
                pressure_Pa=pf, temperature_K=temperature_K, api=api,
                gas_sg=gas_sg, rsb_sm3_sm3=rsb_sm3_sm3)
        else:  # water
            result = compute_brine_properties(pressure_Pa=pf, temperature_K=temperature_K)
        if not metadata and "metadata" in result:
            metadata = result.pop("metadata")
        else:
            result.pop("metadata", None)
        result["pressure_Pa"] = pf
        rows.append(result)
    return {"rows": rows, "metadata": metadata}


_RELPERM_FAMILY = {"BrooksCorey": "COR", "Corey": "COR", "LET": "LET", "Jerauld": "JER"}

_FAMILY_EXPONENTS = {
    "COR": ("nw", "no", "ng"),
    "LET": ("Lw", "Ew", "Tw", "Lo", "Eo", "To", "Lg", "Eg", "Tg"),
    "JER": ("aw", "bw", "ao", "bo", "ag", "bg"),
}
_FAMILY_DEFAULTS = {
    "COR": {"nw": 3.0, "no": 2.0, "ng": 2.0},
    "LET": {"Lw": 2.0, "Ew": 1.5, "Tw": 1.5, "Lo": 2.5, "Eo": 1.25, "To": 1.75,
            "Lg": 2.0, "Eg": 1.5, "Tg": 1.5},
    "JER": {"aw": 1.0, "bw": 1.0, "ao": 1.0, "bo": 1.0, "ag": 1.0, "bg": 1.0},
}
# Library column -> output key, per table type. rel_perm_table produces no Pc
# column; capillary pressure comes from generate_cap_pressure.
_TABLE_OUTPUT_KEYS = {
    "SWOF": {"Sw": "Sw", "Krwo": "Krw", "Krow": "Kro"},
    "SGOF": {"Sg": "Sg", "Krgo": "Krg", "Krog": "Kro"},
    "SGWFN": {"Sg": "Sg", "Krgw": "Krg", "Krwg": "Krw"},
}


@mcp.tool
def generate_rel_perm(
    model: str,
    swc: float,
    sorg: float,
    exponents: dict,
    n_rows: int = 50,
    table: str = "SWOF",
) -> list[dict] | dict:
    """Generate a relative permeability table (Corey, LET, or Jerauld family).

    Args:
        model: Rel-perm family: "BrooksCorey" (or "Corey"), "LET", or "Jerauld".
        swc: Connate water saturation.
        sorg: Residual saturation of the other (non-wetting) phase. Mapped to
              the library's sorw for SWOF and sorg for SGOF; unused for SGWFN.
        exponents: Family parameters. Corey: nw/no/ng; LET: Lw,Ew,Tw,Lo,Eo,To
                   (plus Lg,Eg,Tg for gas tables); Jerauld: aw,bw,ao,bo
                   (plus ag,bg for gas tables). Missing keys use defaults.
        n_rows: Exact row count of the generated table (upstream pyResToolbox
                >=3.7 sizes the grid to the requested row count precisely).
        table: "SWOF" (water-oil), "SGOF" (gas-oil), or "SGWFN" (gas-water).

    Capillary pressure is not part of these tables; use generate_cap_pressure.
    """
    from agents4geos.fluids import si_adapter as simtools

    fam = _RELPERM_FAMILY.get(model)
    if fam is None:
        return {"error": f"Unsupported rel-perm model '{model}'. "
                         f"Supported: BrooksCorey, LET, Jerauld. "
                         f"For Van Genuchten capillary pressure use generate_cap_pressure."}
    if table not in _TABLE_OUTPUT_KEYS:
        return {"error": f"Unsupported table '{table}'. Supported: SWOF, SGOF, SGWFN."}

    kwargs: dict = {"rows": n_rows, "krtable": table, "krfamily": fam}
    if table == "SWOF":
        kwargs.update({"swc": swc, "swcr": swc, "sorw": sorg})
    elif table == "SGOF":
        kwargs.update({"swc": swc, "sorg": sorg})
    else:  # SGWFN
        kwargs.update({"swc": swc})

    defaults = _FAMILY_DEFAULTS[fam]
    kwargs.update({name: float(exponents.get(name, defaults[name]))
                   for name in _FAMILY_EXPONENTS[fam]})

    df = simtools.rel_perm_table(**kwargs)
    out_keys = _TABLE_OUTPUT_KEYS[table]
    return [{out: float(row[col]) for col, out in out_keys.items()}
            for _, row in df.iterrows()]


@mcp.tool
def fit_rel_perm(
    measured_S: list[float],
    measured_Kr: list[float],
    model: str = "BrooksCorey",
    krmax: float = 1.0,
    s_min: float = 0.0,
    s_max: float = 1.0,
) -> dict:
    """Fit a relative permeability model (BrooksCorey, LET, or Jerauld) to measured data.

    Args:
        measured_S: Saturation values (water or gas) of the measured points.
        measured_Kr: Measured relative permeability at each saturation.
        model: "BrooksCorey" (or "Corey"), "LET", or "Jerauld".
        krmax: Endpoint kr the model is scaled by.
        s_min: Critical/connate saturation endpoint used to normalize S.
        s_max: Maximum saturation endpoint used to normalize S.
    """
    from agents4geos.fluids import si_adapter as simtools

    fam = _RELPERM_FAMILY.get(model)
    if fam is None:
        return {"error": f"Unsupported model '{model}'. Supported: BrooksCorey, LET, Jerauld."}

    res = simtools.fit_rel_perm(sw=measured_S, kr=measured_Kr, krfamily=fam,
                                krmax=krmax, sw_min=s_min, sw_max=s_max)
    return {
        "model": model,
        "parameters": {k: float(v) for k, v in res["params"].items()},
        "ssq": float(res["ssq"]),
        "krmax": float(res["krmax"]),
        "sw_min": float(res["sw_min"]),
        "sw_max": float(res["sw_max"]),
    }


@mcp.tool
def generate_cap_pressure(
    model: str,
    entry_pressure_Pa: float,
    swc: float,
    exponent: float,
    n_rows: int = 50,
) -> list[dict]:
    """Generate a capillary pressure curve (all SI units)."""
    sw = np.linspace(swc + 0.01, 1.0, n_rows)
    se = (sw - swc) / (1.0 - swc)

    if model == "BrooksCorey":
        pc = entry_pressure_Pa * se ** (-1.0 / exponent)
    else:  # VanGenuchten
        pc = entry_pressure_Pa * ((se ** (-1.0 / exponent) - 1) ** (1.0 - exponent))

    return [{"Sw": float(s), "Pc_Pa": float(p)} for s, p in zip(sw, pc)]


@mcp.tool
def compute_well_ipr(
    reservoir_pressure_Pa: float,
    temperature_K: float,
    permeability_m2: float,
    thickness_m: float,
    wellbore_radius_m: float,
    drainage_radius_m: float,
    fluid_type: str = "gas",
    skin: float = 0.0,
    gas_specific_gravity: float = 0.75,
    co2: float = 0.0,
    h2s: float = 0.0,
    n2: float = 0.0,
    n_points: int = 20,
) -> dict:
    """Compute a gas well inflow performance (IPR) curve (all SI units).

    Sweeps flowing bottom-hole pressure from reservoir pressure down to one
    atmosphere and evaluates the Darcy pseudo-steady-state radial rate at
    each point. Oil IPR is deliberately not implemented in this slice.
    """
    from agents4geos.fluids import si_adapter as gas

    if fluid_type != "gas":
        return {"error": "Oil IPR not implemented in this slice; only fluid_type='gas' "
                         "is supported (use pyrestoolbox.oil.oil_rate_radial directly)."}

    floor_Pa = 101325.0  # sweep down to one atmosphere
    pwf_values = np.linspace(reservoir_pressure_Pa, floor_Pa, n_points)
    rates = [float(gas.gas_rate_radial(
                 k=permeability_m2, h=thickness_m, pr=reservoir_pressure_Pa,
                 pwf=float(pwf), r_w=wellbore_radius_m, r_ext=drainage_radius_m,
                 degf=temperature_K, S=skin, sg=gas_specific_gravity,
                 co2=co2, h2s=h2s, n2=n2))
             for pwf in pwf_values]
    return {
        "pwf_Pa": [float(p) for p in pwf_values],
        "rate_m3_s": rates,
        "reservoir_pressure_Pa": reservoir_pressure_Pa,
        "metadata": {
            "method": "Darcy pseudo-steady-state radial flow with gas pseudopressure "
                      "(pyResToolbox.gas.gas_rate_radial)",
            "sweep": f"pwf from reservoir pressure down to {floor_Pa:.0f} Pa (1 atm) "
                     f"in {n_points} points",
            "composition": {"sg": gas_specific_gravity, "co2": co2, "h2s": h2s, "n2": n2},
        },
    }


@mcp.tool
def create_table_rel_perm_xml(
    phase_names: list[str],
    table_data: dict,
) -> dict:
    """Generate GEOS TableRelativePermeability XML + TableFunction definitions.

    2-phase: phase_names has two entries (wetting phase first) and table_data
    maps each phase name to {"saturation": [...], "kr": [...]}; emits
    wettingNonWettingRelPermTableNames.

    3-phase: phase_names must be ["water", "oil", "gas"] (wetting,
    intermediate, non-wetting) and table_data must have keys "water",
    "oil_ow" (oil kr vs oil saturation in the water-oil system), "gas",
    "oil_go" (oil kr vs oil saturation in the gas-oil system); emits
    wettingIntermediateRelPermTableNames and
    nonWettingIntermediateRelPermTableNames.

    Every table maps a phase's own saturation (strictly increasing
    coordinates) to its relative permeability.
    """
    def table_function_xml(func_name: str, data: dict) -> str:
        coords = ", ".join(str(s) for s in data["saturation"])
        values = ", ".join(str(k) for k in data["kr"])
        return (f'<TableFunction name="{func_name}"\n'
                f'  coordinates="{{ {coords} }}"\n'
                f'  values="{{ {values} }}"/>')

    instructions = ("Add TableFunctions to <Functions> section and "
                    "TableRelativePermeability to <Constitutive>. "
                    "Include 'relperm' in materialList.")

    if len(phase_names) == 3:
        if phase_names != ["water", "oil", "gas"]:
            return {"error": "3-phase requires phase_names == ['water', 'oil', 'gas'] "
                             "(wetting, intermediate, non-wetting)."}
        required = ("water", "oil_ow", "gas", "oil_go")
        missing = [k for k in required if k not in table_data]
        if missing:
            return {"error": f"3-phase requires table_data keys {list(required)}; "
                             f"missing: {missing}"}
        for key in required:
            data = table_data[key]
            if len(data["saturation"]) != len(data["kr"]):
                return {"error": f"'{key}': saturation and kr arrays must have same length"}
        func_names = {"water": "waterRelPermTable", "oil_ow": "oilRelPermTable_ow",
                      "gas": "gasRelPermTable", "oil_go": "oilRelPermTable_go"}
        table_functions = [table_function_xml(func_names[k], table_data[k])
                           for k in required]
        phases_str = ", ".join(phase_names)
        relperm_xml = (
            f'<TableRelativePermeability name="relperm"\n'
            f'  phaseNames="{{ {phases_str} }}"\n'
            f'  wettingIntermediateRelPermTableNames='
            f'"{{ waterRelPermTable, oilRelPermTable_ow }}"\n'
            f'  nonWettingIntermediateRelPermTableNames='
            f'"{{ gasRelPermTable, oilRelPermTable_go }}"/>'
        )
        return {
            "relperm_xml": relperm_xml,
            "table_function_xmls": table_functions,
            "table_names": [func_names[k] for k in required],
            "instructions": instructions,
        }

    table_functions = []
    table_names = []
    for phase in phase_names:
        if phase not in table_data:
            return {"error": f"Missing table data for phase '{phase}'"}
        data = table_data[phase]
        if len(data["saturation"]) != len(data["kr"]):
            return {"error": f"Phase '{phase}': saturation and kr arrays must have same length"}
        func_name = f"{phase}RelPermTable"
        table_names.append(func_name)
        table_functions.append(table_function_xml(func_name, data))

    phases_str = ", ".join(phase_names)
    tables_str = ", ".join(table_names)
    relperm_xml = (
        f'<TableRelativePermeability name="relperm"\n'
        f'  phaseNames="{{ {phases_str} }}"\n'
        f'  wettingNonWettingRelPermTableNames="{{ {tables_str} }}"/>'
    )
    return {
        "relperm_xml": relperm_xml,
        "table_function_xmls": table_functions,
        "table_names": table_names,
        "instructions": instructions,
    }


@mcp.tool
def build_table_relperm_xml(
    model: str,
    phase_names: list[str],
    swc: float,
    sor: float,
    exponents: dict,
    n_rows: int = 30,
) -> dict:
    """Generate rel-perm curves and GEOS TableRelativePermeability XML in one call.

    Phase sets: ["water", "gas"] (gas-water SGWFN table), ["water", "oil"]
    (SWOF), or ["water", "oil", "gas"] (SWOF water-oil + SGOF gas-oil).
    Curves come from generate_rel_perm (Corey/LET/Jerauld); XML from
    create_table_rel_perm_xml. Capillary pressure is not included (use
    generate_cap_pressure).

    Args:
        model: "BrooksCorey" (or "Corey"), "LET", or "Jerauld".
        phase_names: One of the three supported phase sets above.
        swc: Connate water saturation.
        sor: Residual saturation of the non-wetting/other phase.
        exponents: Family parameters as in generate_rel_perm.
        n_rows: Approximate rows per table.
    """
    phases = list(phase_names)

    if phases == ["water", "gas"]:
        rows = generate_rel_perm(model=model, swc=swc, sorg=sor,
                                 exponents=exponents, n_rows=n_rows, table="SGWFN")
        if isinstance(rows, dict):
            return rows  # error passthrough
        sg = [r["Sg"] for r in rows]
        # Water table must be kr vs its OWN ascending saturation: Sw = 1 - Sg.
        sw = [1.0 - s for s in reversed(sg)]
        krw = [r["Krw"] for r in reversed(rows)]
        table_data = {"water": {"saturation": sw, "kr": krw},
                      "gas": {"saturation": sg, "kr": [r["Krg"] for r in rows]}}
        return create_table_rel_perm_xml(phase_names=phases, table_data=table_data)

    if phases == ["water", "oil"]:
        rows = generate_rel_perm(model=model, swc=swc, sorg=sor,
                                 exponents=exponents, n_rows=n_rows, table="SWOF")
        if isinstance(rows, dict):
            return rows
        sw = [r["Sw"] for r in rows]
        so = [1.0 - s for s in reversed(sw)]
        kro = [r["Kro"] for r in reversed(rows)]
        table_data = {"water": {"saturation": sw, "kr": [r["Krw"] for r in rows]},
                      "oil": {"saturation": so, "kr": kro}}
        return create_table_rel_perm_xml(phase_names=phases, table_data=table_data)

    if phases == ["water", "oil", "gas"]:
        swof = generate_rel_perm(model=model, swc=swc, sorg=sor,
                                 exponents=exponents, n_rows=n_rows, table="SWOF")
        if isinstance(swof, dict):
            return swof
        sgof = generate_rel_perm(model=model, swc=swc, sorg=sor,
                                 exponents=exponents, n_rows=n_rows, table="SGOF")
        if isinstance(sgof, dict):
            return sgof
        sw = [r["Sw"] for r in swof]
        so_ow = [1.0 - s for s in reversed(sw)]
        kro_ow = [r["Kro"] for r in reversed(swof)]
        sg = [r["Sg"] for r in sgof]
        # Oil saturation in the gas-oil system at connate water: So = 1 - swc - Sg.
        so_go = [1.0 - swc - s for s in reversed(sg)]
        kro_go = [r["Kro"] for r in reversed(sgof)]
        table_data = {
            "water": {"saturation": sw, "kr": [r["Krw"] for r in swof]},
            "oil_ow": {"saturation": so_ow, "kr": kro_ow},
            "gas": {"saturation": sg, "kr": [r["Krg"] for r in sgof]},
            "oil_go": {"saturation": so_go, "kr": kro_go},
        }
        return create_table_rel_perm_xml(phase_names=phases, table_data=table_data)

    return {"error": "Unsupported phase set. Use ['water', 'gas'], "
                     "['water', 'oil'], or ['water', 'oil', 'gas']."}


@mcp.tool
def recommend_fluid_model(description: str) -> dict:
    """Recommend GEOS solver and constitutive models from a natural language description."""
    return recommend_model(description)
