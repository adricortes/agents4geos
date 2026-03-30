"""Fluid & constitutive MCP tools (Group 2) — wraps pyResToolbox with SI units."""

from __future__ import annotations

import numpy as np

from agents4geosx.server import mcp
from agents4geosx.knowledge.fluid_models import recommend_model


@mcp.tool
def compute_gas_properties(
    pressure_Pa: float,
    temperature_K: float,
    specific_gravity: float,
    co2: float = 0.0,
    h2s: float = 0.0,
    n2: float = 0.0,
) -> dict:
    """Compute gas PVT properties at given conditions (all SI units)."""
    from pyrestoolbox import gas

    z = gas.gas_z(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                  co2=co2, h2s=h2s, n2=n2, units="SI")
    rho = gas.gas_den(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                      co2=co2, h2s=h2s, n2=n2, units="SI")
    mu = gas.gas_ug(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                    co2=co2, h2s=h2s, n2=n2, units="SI")
    bg = gas.gas_bg(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                    co2=co2, h2s=h2s, n2=n2, units="SI")
    cg = gas.gas_cg(p=pressure_Pa, sg=specific_gravity, degf=temperature_K,
                    co2=co2, h2s=h2s, n2=n2, units="SI")
    return {
        "z_factor": float(z),
        "density_kg_m3": float(rho),
        "viscosity_Pa_s": float(mu),
        "Bg_m3_m3": float(bg),
        "compressibility_1_Pa": float(cg),
    }


@mcp.tool
def compute_oil_properties(
    pressure_Pa: float,
    temperature_K: float,
    api: float,
    gas_sg: float,
    rsb_sm3_sm3: float,
) -> dict:
    """Compute oil PVT properties at given conditions (all SI units)."""
    from pyrestoolbox import oil

    pb = oil.oil_pbub(api=api, degf=temperature_K, rsb=rsb_sm3_sm3,
                      sg_g=gas_sg, units="SI")
    rs = oil.oil_rs(p=pressure_Pa, pb=pb, api=api, degf=temperature_K,
                    rsb=rsb_sm3_sm3, sg_g=gas_sg, units="SI")
    bo = oil.oil_bo(p=pressure_Pa, pb=pb, api=api, degf=temperature_K,
                    rsb=rsb_sm3_sm3, sg_g=gas_sg, units="SI")
    rho = oil.oil_deno(p=pressure_Pa, api=api, pb=pb, rs=rs, bo=bo, units="SI")
    mu = oil.oil_viso(p=pressure_Pa, api=api, degf=temperature_K,
                      pb=pb, rs=rs, units="SI")
    co = oil.oil_co(p=pressure_Pa, pb=pb, api=api, degf=temperature_K,
                    rs=rs, units="SI")
    return {
        "pb_Pa": float(pb),
        "rs_sm3_sm3": float(rs),
        "bo_m3_m3": float(bo),
        "density_kg_m3": float(rho),
        "viscosity_Pa_s": float(mu),
        "compressibility_1_Pa": float(co),
    }


@mcp.tool
def compute_brine_properties(
    pressure_Pa: float,
    temperature_K: float,
    salinity_wt_pct: float = 0.0,
    co2_saturated: bool = False,
) -> dict:
    """Compute water/brine PVT properties (all SI units)."""
    from pyrestoolbox import brine

    result = brine.brine_props(p=pressure_Pa, degf=temperature_K,
                               wt=salinity_wt_pct, units="SI")
    # brine_props SI returns: (Bw, density_kg_m3, viscosity_Pa_s, [cw_list], Rs_ch4)
    return {
        "density_kg_m3": float(result[1]),
        "viscosity_Pa_s": float(result[2]),
        "Bw": float(result[0]),
        "compressibility_1_Pa": float(result[3][0]) if isinstance(result[3], list) and len(result[3]) > 0 else 0.0,
    }


@mcp.tool
def generate_pvt_table(
    fluid_type: str,
    pressure_range_Pa: list[float],
    temperature_K: float,
    n_rows: int = 50,
) -> list[dict]:
    """Generate a PVT table over a pressure range (all SI units)."""
    pressures = np.linspace(pressure_range_Pa[0], pressure_range_Pa[1], n_rows)
    table = []
    for p in pressures:
        pf = float(p)
        if fluid_type == "gas":
            row = compute_gas_properties(pressure_Pa=pf, temperature_K=temperature_K,
                                         specific_gravity=0.7)
        elif fluid_type == "water":
            row = compute_brine_properties(pressure_Pa=pf, temperature_K=temperature_K)
        else:
            row = {}
        row["pressure_Pa"] = pf
        table.append(row)
    return table


@mcp.tool
def generate_rel_perm(
    model: str,
    swc: float,
    sorg: float,
    exponents: dict,
    n_rows: int = 50,
) -> list[dict]:
    """Generate a relative permeability table."""
    from pyrestoolbox import simtools

    family_map = {"BrooksCorey": "COR", "VanGenuchten": "COR", "LET": "LET"}
    family = family_map.get(model, "COR")

    kwargs: dict = {"rows": n_rows, "krtable": "SWOF", "krfamily": family,
                    "swc": swc, "sorg": sorg}
    if family == "COR":
        kwargs["nw"] = exponents.get("nw", 3.0)
        kwargs["no"] = exponents.get("no", 2.0)
    elif family == "LET":
        kwargs.update({
            "Lw": exponents.get("Lw", 2.0), "Ew": exponents.get("Ew", 1.5),
            "Tw": exponents.get("Tw", 1.5), "Lo": exponents.get("Lo", 2.5),
            "Eo": exponents.get("Eo", 1.25), "To": exponents.get("To", 1.75),
        })

    df = simtools.rel_perm_table(**kwargs)
    # DataFrame columns depend on krtable type — SWOF has Sw, Krw, Krow, Pc
    cols = df.columns.tolist()
    result = []
    for _, row in df.iterrows():
        entry = {"Sw": float(row.iloc[0]), "Krw": float(row.iloc[1]), "Kro": float(row.iloc[2])}
        result.append(entry)
    return result


@mcp.tool
def fit_rel_perm(
    measured_S: list[float],
    measured_Kr: list[float],
    model: str = "BrooksCorey",
) -> dict:
    """Fit a relative permeability model to measured data."""
    from pyrestoolbox import simtools

    family = "COR" if model == "BrooksCorey" else "LET"
    result = simtools.fit_rel_perm(s_measured=measured_S, kr_measured=measured_Kr,
                                   krfamily=family)
    return {"parameters": str(result), "model": model}


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
) -> dict:
    """Compute well inflow performance (IPR) and operating point."""
    from pyrestoolbox import gas

    if fluid_type == "gas":
        rate = gas.gas_rate_radial(
            k=permeability_m2, h=thickness_m, pr=reservoir_pressure_Pa,
            pwf=reservoir_pressure_Pa * 0.5, r_w=wellbore_radius_m,
            r_ext=drainage_radius_m, degf=temperature_K, S=skin, units="SI",
        )
        return {
            "rate_m3_s": float(rate),
            "flowing_pressure_Pa": reservoir_pressure_Pa * 0.5,
            "reservoir_pressure_Pa": reservoir_pressure_Pa,
        }
    return {"error": "Oil IPR not yet implemented"}


@mcp.tool
def recommend_fluid_model(description: str) -> dict:
    """Recommend GEOS solver and constitutive models from a natural language description."""
    return recommend_model(description)
