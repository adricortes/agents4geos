# CO₂-brine

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

GEOS exposes four CO₂-brine fluid variants on two axes: **correlation** (Phillips
vs Ezrokhi for brine density/viscosity) × **temperature treatment** (isothermal
vs thermal). All real deck use lives under `compositionalMultiphaseWell/` and
`compositionalMultiphaseFlow/`; the poromechanics deck families that also
reference these fluids are OUT of scope.

## Variant axes

| Variant | Element | inputFile uses | Default? |
|---------|---------|---------------:|----------|
| Phillips, isothermal | `CO2BrinePhillipsFluid` | 22 | ✅ default |
| Ezrokhi, isothermal | `CO2BrineEzrokhiFluid` | 4 | benchmark-specific |
| Phillips, thermal | `CO2BrinePhillipsThermalFluid` | 4 | non-iso default |
| Ezrokhi, thermal | `CO2BrineEzrokhiThermalFluid` | 0 (schema-only) | ❌ no exemplar |

## Decision rule (stage 2)

- Default to **Phillips isothermal** for any plain "CO₂ storage" / "CO₂
  injection" request. Best validated, widest deck coverage.
- Pick **Ezrokhi isothermal** when the user mentions high-salinity brine,
  residual trapping with hysteresis, or references the SPE Class 09 / Pb3
  benchmark family.
- Pick **Phillips thermal** when the user mentions any non-isothermal physics:
  Joule-Thomson cooling at the wellhead, cold-CO₂ plume, geothermal coupling,
  or references SPE 11 case B.
- **Do not** pick Ezrokhi thermal — the schema accepts it, but no GEOS inputFile
  uses it, so we have no template to adapt. Substitute Phillips thermal and
  note the deviation to the user.

## Entries

### simpleCo2InjTutorial_base — Phillips isothermal

**File:** `compositionalMultiphaseWell/simpleCo2InjTutorial_base.xml`
**One-liner:** Single CO₂ injector into a brine aquifer at 95 °C with volume-rate
control and a 50 MPa BHP cap — the canonical "I want to do CO₂ storage" starter.
**Use as starter when:** the user asks for CO₂ injection / storage / sequestration
without further qualifiers. Sphinx-commented as a tutorial — explicitly meant for
adaptation.

| Tag | Value |
|-----|-------|
| Physics | Compositional 2-component (CO₂, brine), isothermal |
| Solver | `CompositionalMultiphaseReservoir` (couples flow + well), TPFA |
| Fluid | `CO2BrinePhillipsFluid` (Phillips brine correlations, PVT from `phasePVTParaFiles`) |
| Geometry | Set by including deck (base meant to be wrapped) |
| Driving | Single injector, `control="totalVolRate"`, target BHP 50 MPa, injection stream `{1, 0}` = pure CO₂ |
| Temperature | 368.15 K (95 °C) |
| Surface conditions | 101 325 Pa, 288.71 K (standard) |
| Wells | One well, `useSurfaceConditions="1"` (rates expressed at surface) |
| Knowledge-module coverage | ✅ Fluid + materialList + cross-refs all in scope |
| Reuse | ★★★ — primary CO₂ starter |

### class09_pb3_drainageOnly_iterative_base — Ezrokhi isothermal

**File:** `compositionalMultiphaseWell/benchmarks/Class09Pb3/class09_pb3_drainageOnly_iterative_base.xml`
**One-liner:** Deep CO₂ injection (3000 m depth, 90 °C) with three pre-wired
well-control modes (volume-rate-table, mass-rate-fixed, mass-rate-table) — the
benchmark-grade starter for SPE Class 09 problem 3 family.
**Use as starter when:** the user references SPE 09 Pb3 by name, asks for
hysteresis or residual trapping, mentions high-salinity brine, or wants a deck
with prepared mass-rate scheduling. Note the **sibling decks** in the same
directory cover hysteresis (`*_hystRelperm_*`) and direct vs iterative coupling.

| Tag | Value |
|-----|-------|
| Physics | Compositional 2-component, isothermal, deeper/stiffer than simpleCo2InjTutorial |
| Solver | `CompositionalMultiphaseReservoir` with iterative (sequential) coupling — see direct-coupling sibling for fully-implicit |
| Fluid | `CO2BrineEzrokhiFluid` (Ezrokhi brine — better at high TDS) |
| Geometry | Set by including deck (benchmark mesh) |
| Driving | 3 pre-wired well controls — pick one and disable the others by name |
| Temperature | 363 K (90 °C) |
| Reference elevation | −3000 m (deep aquifer) |
| Knowledge-module coverage | ⚠️ `CO2BrineEzrokhiFluid` flagged TODO in 2026-03-30 audit — `fluid_models.py` doesn't yet model it. Adapt with care; validation may miss Ezrokhi-specific rules. Tracked in agents4geos-fot. |
| Reuse | ★★ — purpose-specific benchmark, but high quality |

### co2_thermal_2d — Phillips thermal

**File:** `thermalMultiphaseFlow/co2_thermal_2d.xml`
**One-liner:** 2D thermal CO₂ flow in a 100 × 100 m slice driven by box-defined
source and sink regions (no wells) — the cleanest pedagogical entry into
non-isothermal CO₂ physics.
**Use as starter when:** the user asks for any non-isothermal CO₂ scenario but
doesn't need wells yet. For well-driven thermal CO₂, scale up to the SPE 11
case B deck (`compositionalMultiphaseFlow/benchmarks/SPE11/b/spe11b_vti_source_base.xml`).

| Tag | Value |
|-----|-------|
| Physics | Compositional 2-component CO₂-brine, **thermal** (`isThermal="1"`) |
| Solver | Standalone `CompositionalMultiphaseFVM` (no well solver) |
| Fluid | `CO2BrinePhillipsThermalFluid` (adds T-dependent brine properties) |
| Geometry | 2D slice: 100 m × 100 m × 1 m, 10 × 10 × 1 hex |
| Driving | Box-defined source (1 side) + sink (opposite corner); no wells |
| Temperature | 368.15 K initial; both `targetRelativeTemperatureChangeInTimeStep` and `targetPhaseVolFractionChangeInTimeStep` tuned |
| Timescale | `maxTime=1.5e5` s (≈1.7 days) |
| Knowledge-module coverage | ⚠️ Thermal Phillips variant not explicitly listed in v0.1 README; sanity-rules for temperature range still apply. Tracked in agents4geos-fot and agents4geos-npm. |
| Reuse | ★★★ — primary thermal CO₂ starter |
