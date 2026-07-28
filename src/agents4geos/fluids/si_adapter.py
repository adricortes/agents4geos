"""SI-unit adapter over stock pyResToolbox (PyPI, upstream >= 3.6, field-native).

Replaces the previously-vendored pyResToolbox SI fork. Stock upstream only
speaks FIELD units (psia, degF, mD, ft, cP, lb/cuft, scf/stb, mscf/d) plus an
Eclipse `metric=True` mode (barsa, degC, g/cc) for the brine functions — it
has no SI mode at all. This module is a thin boundary layer: convert SI
inputs to whatever native mode the call needs, invoke the untouched stock
correlation body, convert the result back to SI on exit. The conversion
routes and constants below are copied (values only, not imported) from the
fork's verified reference implementation — see
`~/codes/pyResToolbox-audit/02-*.md`/`.csv` for the file:line provenance of
every route this module replicates.

Public surface (17 symbols, matches `agents4geos.tools.fluid_tools` /
`postproc_tools` call sites minus the fork-only `units="SI"` kwarg):
    gas_z, gas_den, gas_ug, gas_bg, gas_cg, gas_rate_radial,
    oil_pbub, oil_rs, oil_bo, oil_deno, oil_viso, oil_co,
    brine_props, CO2_Brine_Mixture,
    rel_perm_table, fit_rel_perm, gas_matbal

Standard-conditions (SC) basis — the one deliberate semantic change vs the
fork (see plan "ISO SC unification"):
    All standard-volume quantities in this module are ISO-basis
    (15 degC / 101,325 Pa), via `SC_CORRECTION_GAS`:
      - Already ISO in the fork, unchanged here: `gas_bg`, every oil.py
        Rs/GOR path (`oil_pbub`'s rsb, `oil_rs`, `oil_bo`/`oil_deno`/
        `oil_viso`'s rs/rsb, `oil_co`'s rsb), `brine_props`'s Rs_ch4.
      - Field-basis in the fork, corrected here (new, deliberate +0.192%
        shift vs the golden fixtures captured at fork e40b57a):
        `gas_rate_radial`'s output rate, `CO2_Brine_Mixture.Rs`.
"""

from __future__ import annotations

import importlib.metadata

import numpy as np

_MIN_VERSION = (3, 6)


def _check_version() -> None:
    raw = importlib.metadata.version("pyrestoolbox")
    parts = raw.split(".")
    try:
        major, minor = int(parts[0]), int(parts[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(
            f"agents4geos.fluids.si_adapter: could not parse pyrestoolbox "
            f"version string {raw!r}"
        ) from exc
    if (major, minor) < _MIN_VERSION:
        raise RuntimeError(
            f"agents4geos.fluids.si_adapter requires stock pyrestoolbox >= "
            f"{'.'.join(map(str, _MIN_VERSION))} (field-native + metric=True "
            f"brine support); found {raw}. Run `uv sync --all-extras` to "
            f"pick up the pinned version."
        )


_check_version()

from pyrestoolbox import gas as _gas          # noqa: E402
from pyrestoolbox import oil as _oil          # noqa: E402
from pyrestoolbox import brine as _brine      # noqa: E402
from pyrestoolbox import matbal as _matbal    # noqa: E402
from pyrestoolbox import simtools as _simtools  # noqa: E402

# ---------------------------------------------------------------------------
# Conversion constants — VALUES copied from the fork's
# `pyrestoolbox/constants/constants.py` (commit e40b57a). Not imported from
# the fork; this module has no dependency on it.
# ---------------------------------------------------------------------------
PSI_TO_PA = 6894.757
PA_TO_PSI = 1.0 / PSI_TO_PA
CP_TO_PAS = 0.001
INVPSI_TO_INVPA = PA_TO_PSI
LBCUFT_TO_KGM3 = 16.01846337
FT_TO_M = 0.3048
M_TO_FT = 1.0 / FT_TO_M
MD_TO_M2 = 9.869233e-16
M2_TO_MD = 1.0 / MD_TO_M2
BBL_TO_M3 = 0.158987295
CUFT_TO_M3 = 0.028316846592
MSCF_TO_SM3 = 28.316846592
SM3_TO_MSCF = 1.0 / MSCF_TO_SM3
CEL2KEL = 273.15

# Standard-conditions correction (fork constants.py:249-257): re-references
# field standard conditions (60 degF / 14.696 psia) onto ISO/SI standard
# conditions (15 degC / 101,325 Pa). ~+0.192% volume rebasing, not a pure
# unit conversion.
_psc = 14.696          # psia
_tsc = 60.0             # degF
_degF2R = 459.67
_tscr = _tsc + _degF2R  # degR
_psc_si = 101325.0      # Pa
_tsc_si = 288.15        # K
_tsc_field_K = _tscr * 5.0 / 9.0
_psc_field_Pa = _psc * PSI_TO_PA
SC_CORRECTION_GAS = (_tsc_field_K / _psc_field_Pa) / (_tsc_si / _psc_si)

# GOR/Rs conversion with SC correction (fork constants.py:275-276) — used for
# every already-ISO Rs/GOR path (oil.py, brine_props).
SCF_STB_TO_SM3_SM3_SI = (CUFT_TO_M3 / BBL_TO_M3) * SC_CORRECTION_GAS
SM3_SM3_TO_SCF_STB_SI = 1.0 / SCF_STB_TO_SM3_SM3_SI

# Non-Darcy skin coefficient: day/Mscf <-> day/sm3 (fork constants.py).
D_PER_SM3_TO_D_PER_MSCF = MSCF_TO_SM3


def _k_to_degf(degf_k):
    return degf_k * 9.0 / 5.0 - 459.67


# ---------------------------------------------------------------------------
# Gas group — entry: SI -> FIELD; body: stock upstream, field-native,
# unchanged since 3.0.5; exit: FIELD -> SI. (fork gas.py:620-1174, B+M
# classification per 02-gas-infra.md #1.)
# ---------------------------------------------------------------------------

def gas_z(p, sg, degf, zmethod="DAK", cmethod="PMC", co2=0, h2s=0, n2=0, h2=0,
          tc=0, pc=0):
    """Real-gas deviation factor Z (dimensionless). SI in: p [Pa], degf [K]."""
    p_field = np.asarray(p, dtype=float) * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    tc_field = tc * 1.8 if tc > 0 else tc
    pc_field = pc * PA_TO_PSI if pc > 0 else pc
    return _gas.gas_z(p=p_field, sg=sg, degf=degf_field, zmethod=zmethod,
                       cmethod=cmethod, co2=co2, h2s=h2s, n2=n2, h2=h2,
                       tc=tc_field, pc=pc_field)


def gas_den(p, sg, degf, zmethod="DAK", cmethod="PMC", co2=0, h2s=0, n2=0,
            h2=0, tc=0, pc=0):
    """Gas density [kg/m3]. SI in: p [Pa], degf [K]."""
    p_field = np.asarray(p, dtype=float) * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    tc_field = tc * 1.8 if tc > 0 else tc
    pc_field = pc * PA_TO_PSI if pc > 0 else pc
    result = _gas.gas_den(p=p_field, sg=sg, degf=degf_field, zmethod=zmethod,
                           cmethod=cmethod, co2=co2, h2s=h2s, n2=n2, h2=h2,
                           tc=tc_field, pc=pc_field)
    return result * LBCUFT_TO_KGM3


def gas_ug(p, sg, degf, zmethod="DAK", cmethod="PMC", co2=0, h2s=0, n2=0,
           h2=0, tc=0, pc=0, zee=0, ugz=False):
    """Gas viscosity [Pa.s] (or ug*Z if ugz=True). SI in: p [Pa], degf [K]."""
    p_field = np.asarray(p, dtype=float) * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    tc_field = tc * 1.8 if isinstance(tc, (int, float)) and tc > 0 else tc
    pc_field = pc * PA_TO_PSI if isinstance(pc, (int, float)) and pc > 0 else pc
    result = _gas.gas_ug(p=p_field, sg=sg, degf=degf_field, zmethod=zmethod,
                          cmethod=cmethod, co2=co2, h2s=h2s, n2=n2, h2=h2,
                          tc=tc_field, pc=pc_field, zee=zee, ugz=ugz)
    return result * CP_TO_PAS


def gas_bg(p, sg, degf, zmethod="DAK", cmethod="PMC", co2=0, h2s=0, n2=0,
           h2=0, tc=0, pc=0):
    """Gas FVF Bg [rm3/sm3], ISO SC basis (15 degC/101,325 Pa). SI in: p [Pa], degf [K]."""
    p_field = np.asarray(p, dtype=float) * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    tc_field = tc * 1.8 if tc > 0 else tc
    pc_field = pc * PA_TO_PSI if pc > 0 else pc
    result = _gas.gas_bg(p=p_field, sg=sg, degf=degf_field, zmethod=zmethod,
                          cmethod=cmethod, co2=co2, h2s=h2s, n2=n2, h2=h2,
                          tc=tc_field, pc=pc_field)
    return result * SC_CORRECTION_GAS


def gas_cg(p, sg, degf, co2=0, h2s=0, n2=0, h2=0, tc=0, pc=0, zmethod="DAK",
           cmethod="PMC"):
    """Gas compressibility [1/Pa]. SI in: p [Pa], degf [K]."""
    p_field = np.asarray(p, dtype=float) * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    tc_field = tc * 1.8 if tc > 0 else tc
    pc_field = pc * PA_TO_PSI if pc > 0 else pc
    result = _gas.gas_cg(p=p_field, sg=sg, degf=degf_field, co2=co2, h2s=h2s,
                          n2=n2, h2=h2, tc=tc_field, pc=pc_field,
                          zmethod=zmethod, cmethod=cmethod)
    return result * INVPSI_TO_INVPA


def gas_rate_radial(k, h, pr, pwf, r_w, r_ext, degf, zmethod="DAK",
                     cmethod="PMC", S=0, D=0, sg=0.75, co2=0, h2s=0, n2=0,
                     h2=0, tc=0, pc=0, gas_pvt=None):
    """Darcy PSS radial gas rate [m3/s], ISO SC basis.

    ISO SC unification: the fork left this rate on the field-equivalent
    standard-condition basis (60 degF/14.696 psia) even under units='SI'
    (see 02-gas-infra.md Sec.3). This adapter applies SC_CORRECTION_GAS so
    the rate is ISO-basis like gas_bg/oil Rs — the one deliberate,
    documented ~+0.192% shift vs the fork's golden fixture.
    """
    pr_field = np.asarray(pr, dtype=float) * PA_TO_PSI
    pwf_field = np.asarray(pwf, dtype=float) * PA_TO_PSI
    h_field = np.asarray(h, dtype=float) * M_TO_FT
    k_field = np.asarray(k, dtype=float) * M2_TO_MD
    degf_field = _k_to_degf(degf)
    r_w_field = r_w * M_TO_FT
    r_ext_field = r_ext * M_TO_FT
    D_field = D * D_PER_SM3_TO_D_PER_MSCF if D > 0 else D
    if gas_pvt is None:
        tc_field = tc * 1.8 if tc > 0 else tc
        pc_field = pc * PA_TO_PSI if pc > 0 else pc
    else:
        tc_field, pc_field = tc, pc  # already field units on gas_pvt

    result = _gas.gas_rate_radial(
        k=k_field, h=h_field, pr=pr_field, pwf=pwf_field, r_w=r_w_field,
        r_ext=r_ext_field, degf=degf_field, zmethod=zmethod, cmethod=cmethod,
        S=S, D=D_field, sg=sg, co2=co2, h2s=h2s, n2=n2, h2=h2, tc=tc_field,
        pc=pc_field, gas_pvt=gas_pvt,
    )
    return result * MSCF_TO_SM3 / 86400.0 * SC_CORRECTION_GAS


# ---------------------------------------------------------------------------
# Oil group — entry: SI -> FIELD (rs/rsb via the ISO-corrected
# SM3_SM3_TO_SCF_STB_SI, not the plain metric ratio); body: stock upstream,
# unchanged since 3.0.5 apart from oil_co dropping the fork-only unused `pi`
# param; exit: FIELD -> SI. (fork oil.py, 02-oil-brine.md #1.)
# ---------------------------------------------------------------------------

def oil_pbub(api, degf, rsb, sg_g=0, sg_sp=0, pbmethod="VALMC"):
    """Bubble point pressure [Pa]. SI in: degf [K], rsb [sm3/sm3] (ISO)."""
    degf_field = _k_to_degf(degf)
    rsb_field = rsb * SM3_SM3_TO_SCF_STB_SI
    result = _oil.oil_pbub(api=api, degf=degf_field, rsb=rsb_field,
                            sg_g=sg_g, sg_sp=sg_sp, pbmethod=pbmethod)
    return result * PSI_TO_PA


def oil_rs(api, degf, sg_sp, p, pb=0, rsb=0, rsmethod="VELAR",
           pbmethod="VALMC"):
    """Solution GOR Rs [sm3/sm3] (ISO). SI in: degf [K], p/pb [Pa], rsb [sm3/sm3]."""
    degf_field = _k_to_degf(degf)
    p_field = p * PA_TO_PSI
    pb_field = pb * PA_TO_PSI if pb > 0 else pb
    rsb_field = rsb * SM3_SM3_TO_SCF_STB_SI if rsb > 0 else rsb
    result = _oil.oil_rs(api=api, degf=degf_field, sg_sp=sg_sp, p=p_field,
                          pb=pb_field, rsb=rsb_field, rsmethod=rsmethod,
                          pbmethod=pbmethod)
    return result * SCF_STB_TO_SM3_SM3_SI


def oil_bo(p, pb, degf, rs, rsb, sg_o, sg_g=0, sg_sp=0, bomethod="MCAIN",
           denomethod="SWMH"):
    """Oil FVF Bo [rm3/sm3], dimensionless ratio (no SC dependence)."""
    p_field = p * PA_TO_PSI
    pb_field = pb * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    rs_field = rs * SM3_SM3_TO_SCF_STB_SI
    rsb_field = rsb * SM3_SM3_TO_SCF_STB_SI
    return _oil.oil_bo(p=p_field, pb=pb_field, degf=degf_field, rs=rs_field,
                        rsb=rsb_field, sg_o=sg_o, sg_g=sg_g, sg_sp=sg_sp,
                        bomethod=bomethod, denomethod=denomethod)


def oil_deno(p, degf, rs, rsb, sg_g=0, sg_sp=0, pb=1e6, sg_o=0, api=0,
             denomethod="SWMH"):
    """Live oil density [kg/m3]. SI in: p [Pa], degf [K], rs/rsb [sm3/sm3]."""
    p_field = p * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    rs_field = rs * SM3_SM3_TO_SCF_STB_SI
    rsb_field = rsb * SM3_SM3_TO_SCF_STB_SI
    pb_field = pb * PA_TO_PSI if pb != 1e6 else pb  # 1e6 is the fork's "unset" sentinel
    result = _oil.oil_deno(p=p_field, degf=degf_field, rs=rs_field,
                            rsb=rsb_field, sg_g=sg_g, sg_sp=sg_sp,
                            pb=pb_field, sg_o=sg_o, api=api,
                            denomethod=denomethod)
    return result * LBCUFT_TO_KGM3


def oil_viso(p, api, degf, pb, rs):
    """Oil viscosity [Pa.s]. SI in: p/pb [Pa], degf [K], rs [sm3/sm3]."""
    p_field = p * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    pb_field = pb * PA_TO_PSI
    rs_field = rs * SM3_SM3_TO_SCF_STB_SI
    result = _oil.oil_viso(p=p_field, api=api, degf=degf_field, pb=pb_field,
                            rs=rs_field)
    return result * CP_TO_PAS


def oil_co(p, api, degf, sg_sp=0, sg_g=0, pb=0, rsb=0, co_sat=False,
           comethod="EXPLT", zmethod="DAK", rsmethod="VELAR", cmethod="PMC",
           denomethod="SWMH", bomethod="MCAIN", pbmethod="VALMC"):
    """Oil compressibility [1/Pa] (or [co_usat, co_sat] if co_sat=True)."""
    p_field = p * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    pb_field = pb * PA_TO_PSI if pb > 0 else pb
    rsb_field = rsb * SM3_SM3_TO_SCF_STB_SI if rsb > 0 else rsb
    result = _oil.oil_co(p=p_field, api=api, degf=degf_field, sg_sp=sg_sp,
                          sg_g=sg_g, pb=pb_field, rsb=rsb_field,
                          co_sat=co_sat, comethod=comethod, zmethod=zmethod,
                          rsmethod=rsmethod, cmethod=cmethod,
                          denomethod=denomethod, bomethod=bomethod,
                          pbmethod=pbmethod)
    if co_sat:
        return [v * INVPSI_TO_INVPA for v in result]
    return result * INVPSI_TO_INVPA


# ---------------------------------------------------------------------------
# Brine group — entry: SI -> METRIC (Pa->bar /1e5, K->degC -273.15), body:
# stock upstream metric=True (bar/degC internally converts to field before
# running the identical correlation body — numerically equivalent to a
# direct SI->FIELD route), exit: METRIC -> SI. (fork brine.py, 02-oil-brine.md #2.)
# ---------------------------------------------------------------------------

def brine_props(p, degf, wt=0, ch4_sat=0):
    """Brine PVT properties, SI. Returns (Bw, density_kg_m3, viscosity_Pa_s,
    [cw_usat, cw_sat]_1_Pa, Rs_ch4_sm3_sm3). Rs_ch4 is ISO SC basis
    (matches the fork's already-ISO brine_props Rs)."""
    p_bar = p / 1e5
    degc = degf - CEL2KEL
    bw, dens_gcc, visc_cp, cw_invbar, rsw = _brine.brine_props(
        p=p_bar, degf=degc, wt=wt, ch4_sat=ch4_sat, metric=True)
    density_kg_m3 = dens_gcc * 1000.0
    viscosity_pas = visc_cp * CP_TO_PAS
    cw_pa = [c / 1e5 for c in cw_invbar]
    # rsw from metric=True is the plain (non-SC-corrected) sm3/sm3 ratio;
    # apply SC_CORRECTION_GAS to reach the ISO basis the fork's SI branch used.
    rsw_iso = rsw * SC_CORRECTION_GAS
    return (bw, density_kg_m3, viscosity_pas, cw_pa, rsw_iso)


class CO2_Brine_Mixture:
    """Wrapper over stock `pyrestoolbox.brine.CO2_Brine_Mixture` exposing SI
    attributes. Constructor takes pres [Pa], temp [K] (converted to
    bar/degC on entry, exactly as the fork's SI branch did internally).

    Rs is ISO SC basis here (deliberate +0.192% shift vs the fork, which
    left CO2_Brine_Mixture.Rs on the field-equivalent basis — see module
    docstring "ISO SC unification"). Every other attribute matches the
    fork's SI-mode numeric value.
    """

    def __init__(self, pres, temp, ppm=0.0, cw_sat=False):
        pres_bar = pres / 1e5
        temp_c = temp - CEL2KEL
        mix = _brine.CO2_Brine_Mixture(pres=pres_bar, temp=temp_c, ppm=ppm,
                                        metric=True, cw_sat=cw_sat)
        self.x = mix.x
        self.y = mix.y
        self.bDen = [d * 1000.0 for d in mix.bDen]
        self.bVis = [v * CP_TO_PAS for v in mix.bVis]
        self.bw = mix.bw
        self.Rs = mix.Rs * SC_CORRECTION_GAS
        self.Cf_usat = mix.Cf_usat / 1e5
        self.Cf_sat = (mix.Cf_sat / 1e5) if mix.Cf_sat is not None else None
        self.bVisblty = mix.bVisblty / 1e5
        self.rhoGas = mix.rhoGas * 1000.0
        self.ppm_sat = mix.ppm_sat


# ---------------------------------------------------------------------------
# Rel-perm — pure passthrough (dimensionless saturations/kr), untouched by
# the fork's SI work (02-simtools-nodal-matbal.md Sec.1/2).
# ---------------------------------------------------------------------------

def rel_perm_table(*args, **kwargs):
    return _simtools.rel_perm_table(*args, **kwargs)


def fit_rel_perm(*args, **kwargs):
    return _simtools.fit_rel_perm(*args, **kwargs)


# ---------------------------------------------------------------------------
# gas_matbal — entry: p Pa->psia, degf K->degF; Gp is left untouched
# (verified against fork matbal.py: the SI branch never converts Gp, only
# p/pvt_table pressures and degf — OGIP's regression is basis-agnostic for
# Gp/OGIP, so it inherits whatever basis the caller's Gp already uses; see
# 02-simtools-nodal-matbal.md #1 and golden/README.md "gas_matbal
# construction"). .ogip therefore comes out directly in Gp's SI basis with
# no exit conversion needed.
# ---------------------------------------------------------------------------

def gas_matbal(p, Gp, degf, sg=0.65, co2=0, h2s=0, n2=0, h2=0, Wp=None,
               Bw=1.0, We=None, zmethod="DAK", cmethod="PMC",
               pvt_table=None):
    """P/Z gas material balance. SI in: p [Pa], degf [K]; Gp in the caller's
    own units (OGIP comes out in the same basis as Gp, unconverted)."""
    p_field = np.asarray(p, dtype=float) * PA_TO_PSI
    degf_field = _k_to_degf(degf)
    pvt_table_field = None
    if pvt_table is not None:
        pvt_table_field = dict(pvt_table)
        pvt_table_field["p"] = np.asarray(pvt_table["p"], dtype=float) * PA_TO_PSI
    return _matbal.gas_matbal(p=p_field, Gp=Gp, degf=degf_field, sg=sg,
                               co2=co2, h2s=h2s, n2=n2, h2=h2, Wp=Wp, Bw=Bw,
                               We=We, zmethod=zmethod, cmethod=cmethod,
                               pvt_table=pvt_table_field)
