# GEOS Example Catalog (schema v0.1 scope)

This catalog is consumed by the `/geos` orchestrator to pick a sensible starting XML
when a user asks for a simulation in plain English. Each entry describes a deck the
orchestrator can adapt — geometry, BCs, materials, and events get *tweaked*, the
canonical solver wiring stays.

## Scope

In-scope physics (per README §Supported Physics v0.1):

| Category | Fluid / solver elements | Notes |
|----------|-------------------------|-------|
| Single-phase flow | `SinglePhaseFVM`, `SinglePhaseHybridFVM` + `CompressibleSinglePhaseFluid` | TPFA or hybrid FVM; incompressible (compressibility = 0) or compressible variants |
| Thermal single-phase | `isThermal="1"` + `ThermalCompressibleSinglePhaseFluid` + `SolidInternalEnergy` + `SinglePhaseThermalConductivity` | Adds energy equation |
| Compositional multiphase (generic) | `CompositionalMultiphaseFVM`/`HybridFVM` + `CompositionalMultiphaseFluid` (PR EOS) | Full equation-of-state compositional; expensive |
| CO₂-brine — Phillips (isothermal) | `CO2BrinePhillipsFluid` | Default CO₂ storage model; Phillips (1991) brine correlations; needs `phasePVTParaFiles` |
| CO₂-brine — Ezrokhi (isothermal) | `CO2BrineEzrokhiFluid` | Same interface as Phillips, different brine parametrization (better at high salinity) |
| CO₂-brine — Phillips thermal | `CO2BrinePhillipsThermalFluid` (+ `isThermal="1"`) | Non-isothermal CO₂ storage; J-T cooling, cold-plume, geothermal coupling |
| CO₂-brine — Ezrokhi thermal | `CO2BrineEzrokhiThermalFluid` | Schema-defined; **no inputFile coverage** — orchestrator should avoid until exemplar exists |
| Dead oil | `DeadOilFluid` | Oil + water (no gas in solution); requires `tableFiles` for PVT |
| Black oil | `BlackOilFluid` | 3-phase oil+gas+water with PVT tables (Bo, Bg, Rs, Rv); saturated/unsaturated + Stone I/II relperm |
| Wells (single-phase) | `SinglePhaseWell`, `SinglePhaseReservoir` | Coupled flow+well system |
| Wells (compositional) | `CompositionalMultiphaseWell`, `CompositionalMultiphaseReservoir` | All CO₂ and Black-oil deck families use this |

Out-of-scope (deferred): poromechanics, geomechanics, hydraulic fracturing,
acoustic/seismic, induced seismicity, contact mechanics, material-point method,
phase-field, proppant, surface generation, triaxial driver, wellbore-ECP.

## How to read an entry

Each entry has a one-liner, a "use as starter when" hint phrased in user-intent
language, and a tag table the orchestrator uses for matching. The **Reuse** field is
the most important: ★★★ = clean canonical starter, ★★ = usable with caveats,
★ = scenario-specific (orchestrator should clone-and-replace whole subtrees, not
just tweak values).

Prior art: see `docs/knowledge-audit-2026-03-30.md` for the feature-coverage audit
this catalog complements.

---

## Single-phase flow

Source directory: `geos/inputFiles/singlePhaseFlow/` (40 decks total; entries below
are the curated starters — variants like `*_smoke.xml`, `*_benchmark.xml` and
resolution alternates are noted but not given their own entry.)

### incompressible_1d

**File:** `singlePhaseFlow/incompressible_1d.xml`
**One-liner:** 1D incompressible single-phase flow in a 10-cell column with prescribed
pressures at the two ends — the simplest possible flow simulation.
**Use as starter when:** the user wants a textbook flow problem, a sanity check on
the install, or a minimal base to extend toward heterogeneity or multiphase.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, incompressible |
| Solver | `SinglePhaseFVM` (TPFA) |
| Geometry | 1D column (10 m × 1 m × 1 m) |
| Mesh | `InternalMesh`, hex (`C3D8`), 10 × 1 × 1 |
| Driving | Dirichlet pressure BC (5 MPa source, −5 MPa sink at opposite x-ends) |
| Fluid | Water, 1000 kg/m³, 1 cP, compressibility = 0 |
| Rock | Porosity 0.05, perm 2×10⁻¹⁶ m² (very tight) |
| Wells | None |
| Timescale | `maxTime=1.0` — single-step steady-state check |
| Outputs | VTK + restart |
| Reuse | ★★★ |

### sourceFlux_1d

**File:** `singlePhaseFlow/sourceFlux_1d.xml`
**One-liner:** Same 1D column as `incompressible_1d`, but the source is now a
mass-rate `SourceFlux` instead of a fixed pressure — closer to how an injection well
behaves.
**Use as starter when:** the user describes a problem in terms of injected/produced
*rate* (kg/s, m³/day) rather than imposed pressure.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, compressible (5×10⁻¹⁰ 1/Pa) |
| Solver | `SinglePhaseFVM` (TPFA) |
| Geometry | 1D column (10 m × 1 m × 1 m) |
| Mesh | `InternalMesh`, hex, 10 × 1 × 1 |
| Driving | `SourceFlux` (rate-based) at source end, pressure BC at sink end |
| Fluid | Water, 1000 kg/m³, 1 cP, compressibility 5×10⁻¹⁰ 1/Pa |
| Rock | Porosity 0.05, perm 2×10⁻¹⁶ m² |
| Wells | None |
| Timescale | `maxTime=2×10⁴` s (~5.5 h), `forceDt=1000` s |
| Outputs | Silo + restart |
| Reuse | ★★★ |

### 3D_10x10x10_compressible_base

**File:** `singlePhaseFlow/3D_10x10x10_compressible_base.xml`
**One-liner:** 3D compressible water flow in a 10×10×10 m box driven by pressure
BCs at opposite corners — the canonical 3D extension of the 1D starters.
**Use as starter when:** the user asks for a 3D flow demo, wants to add gravity or
heterogeneity, or needs a base to bolt an `Events` section onto. Note: this is a
*base* deck — it expects to be wrapped by a smoke-test or benchmark deck via
`<Included>` (see `3D_10x10x10_compressible_smoke.xml`).

| Tag | Value |
|-----|-------|
| Physics | Single-phase, compressible |
| Solver | `SinglePhaseFVM` (TPFA) |
| Geometry | 3D cube (10 × 10 × 10 m) |
| Mesh | `InternalMesh`, hex, intended to be set by including deck |
| Driving | Pressure BC, source at low-corner cell, sink at high-corner cell |
| Fluid | Water, compressible (5×10⁻¹⁰ 1/Pa) |
| Rock | Porosity 0.05, perm anisotropic (1×10⁻¹² m² horizontal, 1×10⁻¹⁵ m² vertical) |
| Wells | None |
| Timescale | Defined by including deck |
| Outputs | Silo |
| Reuse | ★★★ — but pair with a smoke/benchmark wrapper for runnable cases |

### FieldCaseTutorial3_Isothermal_base

**File:** `singlePhaseFlow/FieldCaseTutorial3_Isothermal_base.xml`
**One-liner:** Realistic field-case starter on an external VTK mesh (synthetic
reservoir geometry), with pressure-driven flow — the "this looks like real work"
upgrade from the toy boxes above.
**Use as starter when:** the user references a real reservoir, mentions an external
mesh file (`.vtu`/`.vtm`), or wants any deck that's not a structured cube.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, isothermal, compressible |
| Solver | `SinglePhaseFVM` |
| Geometry | Synthetic field-scale reservoir from external mesh |
| Mesh | `VTKMesh` (`synthetic.vtu` + `synthetic.vtpc`) |
| Driving | Pressure BCs (see paired `_smoke.xml` for full event/BC wiring) |
| Fluid | Water, compressible |
| Rock | Heterogeneous (loaded from mesh attributes) |
| Wells | See related `compositionalMultiphaseWell/FieldCaseTutorial3_*` for well-driven version |
| Timescale | Days-to-years (set by smoke wrapper) |
| Outputs | VTK |
| Reuse | ★★★ — the only field-realistic starter in this category |

---

## Compositional multiphase flow (stub)

Source directory: `geos/inputFiles/compositionalMultiphaseFlow/` (60 decks).
Entries TBD — see follow-up ticket.

## CO₂-brine

GEOS exposes four CO₂-brine fluid variants on two axes: **correlation** (Phillips vs
Ezrokhi for brine density/viscosity) × **temperature treatment** (isothermal vs
thermal). All real deck use lives under `compositionalMultiphaseWell/` and
`compositionalMultiphaseFlow/`; the poromechanics deck families that also reference
these fluids are OUT of scope.

**Choosing between variants (decision rule for the orchestrator)**:

- Default to **Phillips isothermal** for any plain "CO₂ storage" / "CO₂ injection"
  request. Best validated, widest deck coverage (22 inputFile uses).
- Pick **Ezrokhi isothermal** when the user mentions high-salinity brine, residual
  trapping with hysteresis, or references the SPE Class 09 / Pb3 benchmark family.
- Pick **Phillips thermal** when the user mentions any non-isothermal physics:
  Joule-Thomson cooling at the wellhead, cold-CO₂ plume, geothermal coupling, or
  references SPE 11 case B.
- **Do not** pick Ezrokhi thermal — the schema accepts it, but no GEOS inputFile uses
  it, so we have no template to adapt. Substitute Phillips thermal and note the
  deviation to the user.

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
**Use as starter when:** the user references SPE 09 Pb3 by name, asks for hysteresis
or residual trapping, mentions high-salinity brine, or wants a deck with prepared
mass-rate scheduling. Note the **sibling decks** in the same directory cover
hysteresis (`*_hystRelperm_*`) and direct vs iterative coupling.

| Tag | Value |
|-----|-------|
| Physics | Compositional 2-component, isothermal, deeper/stiffer than simpleCo2InjTutorial |
| Solver | `CompositionalMultiphaseReservoir` with iterative (sequential) coupling — see direct-coupling sibling for fully-implicit |
| Fluid | `CO2BrineEzrokhiFluid` (Ezrokhi brine — better at high TDS) |
| Geometry | Set by including deck (benchmark mesh) |
| Driving | 3 pre-wired well controls — pick one and disable the others by name |
| Temperature | 363 K (90 °C) |
| Reference elevation | −3000 m (deep aquifer) |
| Knowledge-module coverage | ⚠️ `CO2BrineEzrokhiFluid` flagged TODO in 2026-03-30 audit — fluid_models.py doesn't yet model it. Adapt with care; validation may miss Ezrokhi-specific rules. |
| Reuse | ★★ — purpose-specific benchmark, but high quality |

### co2_thermal_2d — Phillips thermal

**File:** `thermalMultiphaseFlow/co2_thermal_2d.xml`
**One-liner:** 2D thermal CO₂ flow in a 100 × 100 m slice driven by box-defined
source and sink regions (no wells) — the cleanest pedagogical entry into
non-isothermal CO₂ physics.
**Use as starter when:** the user asks for any non-isothermal CO₂ scenario but
doesn't need wells yet. For well-driven thermal CO₂, scale up to the SPE 11 case B
deck (`compositionalMultiphaseFlow/benchmarks/SPE11/b/spe11b_vti_source_base.xml`).

| Tag | Value |
|-----|-------|
| Physics | Compositional 2-component CO₂-brine, **thermal** (`isThermal="1"`) |
| Solver | Standalone `CompositionalMultiphaseFVM` (no well solver) |
| Fluid | `CO2BrinePhillipsThermalFluid` (adds T-dependent brine properties) |
| Geometry | 2D slice: 100 m × 100 m × 1 m, 10 × 10 × 1 hex |
| Driving | Box-defined source (1 side) + sink (opposite corner); no wells |
| Temperature | 368.15 K initial; both `targetRelativeTemperatureChangeInTimeStep` and `targetPhaseVolFractionChangeInTimeStep` tuned |
| Timescale | `maxTime=1.5e5` s (≈1.7 days) |
| Knowledge-module coverage | ⚠️ Thermal Phillips variant not explicitly listed in v0.1 README; sanity-rules for temperature range still apply |
| Reuse | ★★★ — primary thermal CO₂ starter |

## Black oil

Source directory: `compositionalMultiphaseWell/` — all 4 Black Oil decks live here
(none in compositional flow without wells, none in poromechanics). The variants form
a 2×2 grid: **saturated / unsaturated** (above / below bubble point) × **Stone I /
Stone II** (3-phase relperm interpolation model).

**Choosing between variants (decision rule for the orchestrator)**:

- Default to **saturated + Stone-I** for any plain "black oil" / "oil + gas + water"
  / "depletion drive" request — it's the default-default that GEOS itself ships as
  the unsuffixed example.
- Pick **unsaturated** when the user describes oil below bubble point (Rs < Rs_max,
  no free gas phase initially), undersaturated drainage, or pressure-maintained
  history matches.
- Pick **Stone-II** when the user mentions intermediate-wet relperm, asphalt-water
  systems, or specifically asks for "Stone 2" / "modified Stone".
- All four decks use the **same** mesh, wells, and PVT table structure — variants
  differ only in initial composition (saturated vs unsat) and the relperm model
  identifier. The orchestrator can clone the canonical entry and swap.

### black_oil_wells_saturated_3d — saturated, Stone-I

**File:** `compositionalMultiphaseWell/black_oil_wells_saturated_3d.xml`
**One-liner:** Producer + water-injector pair in a 200×200×10 m oil reservoir
above bubble point with free gas, default Stone-I 3-phase relperm — the textbook
"black-oil waterflood" starter.
**Use as starter when:** the user asks for black-oil simulation, waterflood, oil
production with gas cap, or doesn't specify Stone-I vs Stone-II.

| Tag | Value |
|-----|-------|
| Physics | 3-component black oil (oil, gas, water), isothermal |
| Solver | `CompositionalMultiphaseReservoir` |
| Fluid | `BlackOilFluid` with PVT tables (Bo, Bg, Rs, viscosities); component order **oil, gas, water** |
| Relperm | Stone-I (default — `BrooksCoreyStone2RelativePermeability` is the explicit Stone-II equivalent) |
| Geometry | 3D box, 200 × 200 × 10 m, 4 × 4 × 2 = 32 cells (small; scale up for real cases) |
| Driving | One producer (BHP 12 MPa, target oil rate 0.05 m³/s), one injector (BHP 20 MPa, pure water stream `{0, 0, 1}`) |
| Wells | `InternalWell` defined inside `InternalMesh`, single perforation each, polyline geometry |
| Temperature | 297.15 K (24 °C) — surface-like, typical for shallow black-oil exemplars |
| Initial dt | 86 400 s (1 day) |
| Knowledge-module coverage | ⚠️ Black oil not in v0.1 README list; needs `fluid_models.py` entry. Stone-I/II relperm not in `relperm_models` yet. |
| Reuse | ★★★ — primary black-oil starter; the unsaturated and Stone-II siblings reuse this skeleton |

### Sibling variants (no separate entries)

- `black_oil_wells_saturated_3d_stone2.xml` — same as above with Stone-II relperm
- `black_oil_wells_unsaturated_3d.xml` — same skeleton, undersaturated initial composition
- `black_oil_wells_unsaturated_3d_stone2.xml` — combination of the two above

## Dead oil

`DeadOilFluid` is the most prevalent compositional fluid model in inputFiles/ — 31
total decks, of which 25 are v0.1 in-scope (21 in `compositionalMultiphaseFlow/`,
4 in `compositionalMultiphaseWell/`). The 6 OUT cases live in
`multiphaseFlowFractures/` (5) and `poromechanics/` (1).

**Naming caveat (important)**: `DeadOilFluid` is really a generic
*"multi-phase immiscible no-mass-transfer fluid container"*. Despite the name, it
shows up modelling CO₂-water systems too — e.g.
`compositionalMultiphaseFlow/benchmarks/buckleyLeverettProblem/buckleyLeverett_base.xml`
uses `phaseNames="{ gas, water }"` with `componentMolarWeight="{ 44e-3, 18e-3 }"`
(CO₂ + water) as an analytical-reference proxy. The orchestrator should NOT refuse
`DeadOilFluid` starters just because the user described a non-oil scenario.

**Hard external dependency**: every `DeadOilFluid` element references one
`tableFiles` array of PVT data files (`pvdo.txt`, `pvdg.txt`, `pvtw.txt` patterns)
that live next to the XML, usually under a `tables_*/` or `*_table/` subdirectory.
**When the orchestrator clones a dead-oil starter, it MUST also copy or
path-rewrite these tables** — they're not embedded in the XML, and a missing table
file will fail at deck-load time before any sanity check runs.

### Variant axes

- **Phase count**: 2-phase (oil-water OR gas-water) vs 3-phase (oil-gas-water with
  free gas above bubble point). Phase count is set by `phaseNames` and must match
  the component count in `surfaceDensities`, `componentMolarWeight`, and
  `tableFiles`.
- **3-phase relperm interpolation** (when 3-phase only):
  | Filename suffix | Element | When to pick |
  |-----------------|---------|--------------|
  | _(none — default)_ | `BrooksCoreyRelativePermeability` | Corey-style with implicit Stone-I 3-phase interpolation. Default for textbook cases. |
  | `_corey` | Same element, sometimes named explicitly | Same as above; suffix used to disambiguate from Stone/Baker variants in sibling decks. |
  | `_stone2` | `BrooksCoreyStone2RelativePermeability` | When the user mentions Stone-II, intermediate-wet relperm, or asphalt-water systems. |
  | `_baker` | `BrooksCoreyBakerRelativePermeability` | When the user explicitly asks for Baker interpolation. Less common than Stone variants. |
- **Driving**: BC-driven (Box source/sink regions, standalone `CompositionalMultiphaseFVM`) vs well-driven (`CompositionalMultiphaseReservoir` coupling flow + well).

**Decision rule for the orchestrator**:

- For "waterflood" / "oil + water + gas" / "produce oil while injecting water":
  → 3-phase well-driven, Stone-I default. Start from `dead_oil_wells_2d`; scale
  geometry as needed.
- For a *benchmark-grade* multi-well case: → start from `deadOilEgg_base_direct`
  (Egg benchmark, 12 wells, well-validated in the literature).
- For "verify my install / compare to analytical front position":
  → `buckleyLeverett_base` (2-phase, analytical reference, no wells).
- For a *minimal* academic 3-phase case to extend:
  → `deadoil_3ph_corey_1d` (1D, BC-driven, smallest 3-phase entry).
- If the user mentions Stone-II, Baker, or hysteresis: swap the relperm element
  per the table above. Stone-II and Baker siblings exist for several of the
  starters — search `compositionalMultiphaseFlow/deadoil_3ph_stone2_1d.xml`,
  `deadoil_3ph_baker_1d.xml`, etc.

### dead_oil_wells_2d — 3-phase well-driven waterflood (2D)

**File:** `compositionalMultiphaseWell/dead_oil_wells_2d.xml`
**One-liner:** 2D waterflood demonstrator in a 15×15 m square with two producers
(BHP and phase-rate controlled) and one water injector — the textbook "oil
production + water injection" starter.
**Use as starter when:** the user describes a waterflood, asks for "oil
production with water injection", or wants a small but realistic multi-well
scenario without committing to the Egg benchmark's complexity.

| Tag | Value |
|-----|-------|
| Physics | 3-phase dead oil (oil, gas, water) |
| Solver | `CompositionalMultiphaseReservoir` (couples flow + well), TPFA |
| Fluid | `DeadOilFluid`, 3-component, requires external PVT `tableFiles` |
| Relperm | `BrooksCoreyRelativePermeability` (Corey / Stone-I default) |
| Geometry | 2D plate, 15 × 15 × 1 m, 20 × 20 × 1 = 400 cells |
| Driving | 2 producers (one BHP-controlled with table, one phaseVolRate; both `targetPhaseName="oil"`), 1 injector (water stream `{0, 0, 1}`, totalVolRate, BHP cap 45 MPa) |
| Temperature | 297.15 K (24 °C, surface-like — matches the black-oil convention for this category) |
| Surface conditions | `useSurfaceConditions="1"`, 101 325 Pa, 297.15 K |
| External artifacts | PVT `tableFiles` (oil PVdo, gas PVdg, water PVtw) — must be copied alongside the XML |
| Knowledge-module coverage | ⚠️ `DeadOilFluid` is in the v0.1 README list but the `tableFiles` cross-ref is flagged TODO in the 2026-03-30 audit — sanity checks may not verify table existence |
| Reuse | ★★★ — primary dead-oil starter |

### deadOilEgg_base_direct — Egg benchmark (3D, 12 wells)

**File:** `compositionalMultiphaseWell/benchmarks/Egg/deadOilEgg_base_direct.xml`
**One-liner:** Heriot-Watt Egg benchmark — a 3D channelized reservoir with 8
water injectors and 4 producers all under BHP control — the canonical
multi-well dead-oil reference case.
**Use as starter when:** the user references "Egg model" / "Egg benchmark" by
name, asks for a *realistic* multi-well scenario, or wants a literature-validated
case for history-matching or optimization demos. Pair with the `_iterative`
sibling for sequential coupling.

| Tag | Value |
|-----|-------|
| Physics | 3-phase dead oil, isothermal |
| Solver | `CompositionalMultiphaseReservoir`, direct linear solver (see sibling for iterative) |
| Fluid | `DeadOilFluid` with PVT tables (3-component) |
| Geometry | Egg-shaped channelized reservoir (set by including deck — base meant for inclusion) |
| Driving | 8 injectors + 4 producers, all BHP-controlled (placeholder target rates 1e6 m³/s — BHP is the actual limiter) |
| Temperature | 297.15 K |
| Initial dt | 1e4 s (~2.8 h) |
| Coupling robustness | `maxCompFractionChange="0.5"` (well solver), `0.3` (flow solver) — looser than default to ride the many wells |
| Knowledge-module coverage | ⚠️ As above — `tableFiles` cross-ref not yet wired |
| Reuse | ★★★ — primary multi-well dead-oil benchmark |

### buckleyLeverett_base — 2-phase analytical reference

**File:** `compositionalMultiphaseFlow/benchmarks/buckleyLeverettProblem/buckleyLeverett_base.xml`
**One-liner:** 1D 2-phase (gas-water as a CO₂-water analog) immiscible
displacement with an analytical Buckley-Leverett reference solution — the
go-to "is my install correct?" deck and the only catalog entry whose answer
you can compute by hand.
**Use as starter when:** the user wants to verify a fresh install / regression,
asks for a 1D analytical-reference case, or needs a *cheapest-possible*
compositional-multiphase smoke test. Note the **misleading name** — this is a
CO₂-water proxy, not an oil-water case.

| Tag | Value |
|-----|-------|
| Physics | 2-phase immiscible, no mass transfer; phases are gas + water (CO₂ analog) |
| Solver | Standalone `CompositionalMultiphaseFVM` (no wells, no Reservoir coupling) |
| Fluid | `DeadOilFluid` with `phaseNames="{ gas, water }"` and CO₂+water molecular weights `{44e-3, 18e-3}` |
| Relperm | `BrooksCoreyRelativePermeability`, 2-phase, equal-exponent (3.5, 3.5) — classical |
| Geometry | 1D, set by including deck |
| Driving | Box-defined source/sink at the two ends |
| Temperature | 300 K |
| External artifacts | `buckleyLeverett_table/pvdg.txt` + `pvtw.txt` |
| Knowledge-module coverage | ⚠️ Same `tableFiles` caveat. Also: 2-phase `DeadOilFluid` usage isn't called out separately in v0.1 docs — orchestrator should not assume "3 components always" for this family. |
| Reuse | ★★★ — install-sanity gold standard |

### deadoil_3ph_corey_1d — minimal 3-phase, no wells

**File:** `compositionalMultiphaseFlow/deadoil_3ph_corey_1d.xml`
**One-liner:** 1D 3-phase dead oil driven by box source/sink — the smallest
possible 3-phase deck, intended as an academic starting point to extend toward
2D/3D, wells, or alternative relperm.
**Use as starter when:** the user wants to *explore* 3-phase physics in
isolation, or needs a tiny deck to attach a new feature to (heterogeneity,
gravity, capillary pressure tweaks) without the noise of a full reservoir
configuration.

| Tag | Value |
|-----|-------|
| Physics | 3-phase dead oil, isothermal |
| Solver | Standalone `CompositionalMultiphaseFVM` (no wells) |
| Fluid | `DeadOilFluid` 3-component |
| Relperm | `BrooksCoreyRelativePermeability` (Corey / Stone-I default) |
| Geometry | 1D column, 10 × 1 × 1 m, 10 × 1 × 1 |
| Driving | Box-defined source/sink at ends |
| Temperature | 300 K |
| Timescale | `maxTime=2e7` s (~231 days); **two-stage event scheduling** (forceDt=1e4 for first 1e5 s, then forceDt=1e5) — orchestrator should preserve this pattern when scaling up |
| External artifacts | Colocated PVT tables |
| Knowledge-module coverage | ⚠️ Same `tableFiles` caveat |
| Reuse | ★★★ — academic 3-phase entry point |

### Sibling variants (no separate entries — pick by suffix)

Within `compositionalMultiphaseFlow/` the dead-oil 3-phase 1D family has
prepared variants the orchestrator can swap directly:

- `deadoil_3ph_stone2_1d.xml` — same as `_corey_1d` with Stone-II relperm
- `deadoil_3ph_baker_1d.xml` — same with Baker interpolation
- `deadoil_3ph_staircase_3d.xml` — 3D staircase geometry, same fluid model
- `deadoil_3ph_staircase_hybrid_3d.xml` — same but with `SinglePhaseHybridFVM`-style hybrid FV discretization
- `deadoil_2ph_staircase_gravity_segregation_3d.xml` — 2-phase 3D gravity-segregation test (capillary/buoyancy equilibrium check)
- `grav_seg_1d.xml`, `grav_seg_c1ppu_base.xml`, `grav_seg_base.xml` — gravity-segregation 1D variants (one uses the C1-PPU upwind discretization)
- SPE 10 layer 84/85 benchmark: `benchmarks/SPE10/deadOilSpe10Layers84_85_base_{direct,iterative}.xml` — heterogeneous permeability benchmark

## Thermal-coupled single-phase (stub)

Source decks: `singlePhaseFlow/thermalCompressible_*.xml` + `FieldCaseTutorial3_Thermal_*`.
Pattern: `isThermal="1"` + `ThermalCompressibleSinglePhaseFluid` + `SolidInternalEnergy`
+ `SinglePhaseThermalConductivity`. Entries TBD — see follow-up ticket.

## Wells (single-phase + compositional) (stub)

Source directories: `singlePhaseWell/` (8 decks), `compositionalMultiphaseWell/` (43 decks),
plus the wellbore-physics dirs (which are mostly OUT — wellboreECP uses extra physics).
Entries TBD — see follow-up ticket.

## Immiscible multiphase (stub)

Source directory: `geos/inputFiles/immiscibleMultiphaseFlow/` (8 decks).
The audit flags this as a backlog item (`TwoPhaseImmiscibleFluid` not yet in
`fluid_models.py`). Entries TBD once `fluid_models.py` supports it — file as a
blocker on the relevant fluid-models ticket.

---

## Out-of-scope (counts, no entries)

| Directory | Deck count | Reason out |
|-----------|-----------:|------------|
| `poromechanicsFractures/` | 67 | Poromechanics + fractures |
| `hydraulicFracturing/` | 59 | Hydrofrac solver |
| `poromechanics/` | 57 | Poromechanics |
| `wavePropagation/` | 56 | Acoustic/seismic |
| `lagrangianContactMechanics/` | 49 | Contact mechanics |
| `solidMechanics/` | 43 | Geomechanics |
| `wellboreECP/` | 38 | Extended coupled physics in wellbore |
| `thermoPoromechanics/` | 17 | Poromechanics |
| `singlePhaseFlowFractures/` | 16 | Fractures |
| `thermalSinglePhaseFlowFractures/` | 16 | Fractures |
| `inducedSeismicity/` | 15 | Induced seismicity |
| `efemFractureMechanics/` | 15 | Fracture mechanics |
| `phaseField/` | 14 | Phase field |
| `thermoPoromechanicsFractures/` | 9 | Poromechanics + fractures |
| `proppant/` | 9 | Proppant transport |
| `multiscalePreconditioner/` | 9 | Numerical-method test (not a physics scenario) |
| `triaxialDriver/` | 8 | Lab-scale triaxial test driver (solid) |
| `multiphaseFlowFractures/` | 7 | Fractures |
| `materialPointMethod/` | — | MPM |
| `surfaceGeneration/` | — | Surface generation |
| `multipleMeshBodies/`, `initialization/`, `meshGeneration/`, `simplePDE/`, `relpermDriver/` | — | Infrastructure/drivers, not physics scenarios |

Total out-of-scope decks: ~550 of 716 (~77%). The orchestrator should never pick from these.
