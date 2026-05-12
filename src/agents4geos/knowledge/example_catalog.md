# GEOS Example Catalog (schema v0.1) — Router

This file is the **stage-1 router** consumed by the `/geos` orchestrator. Its
job is to identify the right *category* for a user request and point at the
per-category detail file in `examples/`. The orchestrator should not need to
load any detail file unless it has first matched a category here.

> **Two-stage routing**:
> 1. **Stage 1 (this file)** — Match user intent → category → detail file.
> 2. **Stage 2 (the category file in `examples/`)** — Pick the specific
>    starter, apply the variant-axes decision rule, prepare the adaptation.

## Scope (v0.1)

In-scope physics:

| Category | Fluid / solver elements | Notes |
|----------|-------------------------|-------|
| Single-phase flow | `SinglePhaseFVM`, `SinglePhaseHybridFVM` + `CompressibleSinglePhaseFluid` | TPFA or hybrid FVM; incompressible (compressibility = 0) or compressible variants |
| Thermal single-phase | `isThermal="1"` + `ThermalCompressibleSinglePhaseFluid` + `SolidInternalEnergy` + `SinglePhaseThermalConductivity` | Adds energy equation |
| Compositional multiphase (generic) | `CompositionalMultiphaseFVM`/`HybridFVM` + `CompositionalMultiphaseFluid` (PR EOS) | Full equation-of-state compositional; expensive |
| CO₂-brine — Phillips (isothermal) | `CO2BrinePhillipsFluid` | Default CO₂ storage model; Phillips (1991) brine correlations; needs `phasePVTParaFiles` |
| CO₂-brine — Ezrokhi (isothermal) | `CO2BrineEzrokhiFluid` | Same interface as Phillips, different brine parametrization (better at high salinity) |
| CO₂-brine — Phillips thermal | `CO2BrinePhillipsThermalFluid` (+ `isThermal="1"`) | Non-isothermal CO₂ storage; J-T cooling, cold-plume, geothermal coupling |
| CO₂-brine — Ezrokhi thermal | `CO2BrineEzrokhiThermalFluid` | Schema-defined; **no inputFile coverage** — orchestrator should avoid until exemplar exists |
| Dead oil | `DeadOilFluid` | Generic 2-/3-phase immiscible no-mass-transfer container; misleading name (see [dead_oil.md](examples/dead_oil.md)) |
| Black oil | `BlackOilFluid` | 3-phase oil+gas+water with PVT tables (Bo, Bg, Rs, Rv); saturated/unsaturated + Stone I/II relperm |
| Wells (single-phase) | `SinglePhaseWell`, `SinglePhaseReservoir` | Coupled flow+well system |
| Wells (compositional) | `CompositionalMultiphaseWell`, `CompositionalMultiphaseReservoir` | All CO₂ and Black-oil deck families use this |

Out-of-scope (deferred): poromechanics, geomechanics, hydraulic fracturing,
acoustic/seismic, induced seismicity, contact mechanics, material-point method,
phase-field, proppant, surface generation, triaxial driver, wellbore-ECP.

## Stage-1 routing — user intent → category

When the user request contains the cues in the left column, route to the file in
the right column.

| User cue | Category | Detail file |
|----------|----------|-------------|
| "single-phase flow", "incompressible water", "pressure-driven flow", "1D column", "3D box of water" | Single-phase flow | [examples/single_phase_flow.md](examples/single_phase_flow.md) |
| "thermal flow", "heat transport", "non-isothermal water", "geothermal gradient", "cold/hot injection", `isThermal` | Thermal single-phase | [examples/thermal_single_phase.md](examples/thermal_single_phase.md) |
| "CO₂ injection", "CO₂ storage", "sequestration", "Sleipner-like", "Phillips", "Ezrokhi", "supercritical CO₂", SPE 11, SPE 09 / Class 09 | CO₂-brine | [examples/co2_brine.md](examples/co2_brine.md) |
| "waterflood", "oil + gas + water", "black oil", "depletion drive", "Stone-I", "Stone-II" | Black oil | [examples/black_oil.md](examples/black_oil.md) |
| "dead oil", "oil + water", "no gas dissolved", "Buckley-Leverett", "Egg model", "SPE 10", "install sanity check" | Dead oil | [examples/dead_oil.md](examples/dead_oil.md) |
| "compositional", "PR EOS", "EOS-based", "sour gas", "H₂S", "Søreide-Whitson", "lock exchange", "4-component oil-gas" | Compositional multiphase (generic) | [examples/compositional_multiphase.md](examples/compositional_multiphase.md) |
| "two-phase immiscible", `TwoPhaseImmiscibleFluid`, "SPE 10 immiscible", "immiscible Buckley-Leverett", "no mass transfer", "dedicated immiscible solver" | Immiscible | [examples/immiscible.md](examples/immiscible.md) |
| Any well-centric question — "BHP vs rate control", "mass-rate injection", "deviated trajectory", "multi-perforation", "surface conditions", "downhole rate", "cross-flow", "injection temperature", "well solver wiring" | Wells (capability reference, cross-cuts physics) | [examples/wells.md](examples/wells.md) — then back to the matching physics file once the physics is identified |

If the user names a *physics* the orchestrator can't reach (poromechanics,
fractures, wave/seismic, contact, MPM, phase-field, proppant): tell them it's
out of v0.1 scope. Do NOT silently substitute.

## Benchmark cross-reference

When the user names a benchmark by name, route directly:

| Benchmark | Category | Specific entry |
|-----------|----------|----------------|
| Buckley-Leverett (immiscible — dedicated solver) | Immiscible | `immiscibleTwoPhase_BuckleyLeverett/buckleyLeverett_base` |
| Buckley-Leverett (CO₂-water proxy via DeadOilFluid) | Dead oil | `buckleyLeverett_base` |
| SPE 10 (layers 84/85, dead oil) | Dead oil | `deadOilSpe10Layers84_85_base_{direct,iterative}` |
| SPE 10 layer 84 (immiscible) | Immiscible | `immiscibleTwoPhase_SPE10_layer84_base_{direct,iterative}` |
| Egg model | Dead oil | `deadOilEgg_base_direct` (or `_iterative`) |
| SPE Class 09 Pb3 | CO₂-brine | `class09_pb3_drainageOnly_iterative_base` (+ hyst/direct siblings) |
| SPE 11 case B | CO₂-brine | `spe11b_vti_source_base` (Phillips thermal) |
| Field Case Tutorial 3 | Single-phase flow | `FieldCaseTutorial3_Isothermal_base` |
| Lock exchange (Søreide-Whitson) | Compositional multiphase | `soreideWhitson/lockExchange/lockExchange_base` |

## Format conventions (used by all detail files)

Each detail file follows the same structure: a `## Variant axes` block listing
the dimensions of variation, a `## Decision rule (stage 2)` block mapping
user-intent cues to specific entries, the entries themselves, and a sibling
variants section for known-good alternates that don't need their own entry.

**Format exception**: [`examples/wells.md`](examples/wells.md) documents
cross-cutting well *capabilities* (control modes, solver wiring, trajectory
patterns, surface-conditions handling) rather than starter decks. It has no
entries or ★ ratings — every well-driven deck already lives in its physics
file. The wells file is consulted when a user question is about *how to
configure a well*, not which physics to pick.

Each entry exposes:

- **File** — path under `geos/inputFiles/`
- **One-liner** — what the deck does, in plain reservoir-engineering terms
- **Use as starter when** — user-intent triggers, never tool-mechanic triggers
- **Tag table** — physics / solver / fluid / geometry / wells / etc.
- **Knowledge-module coverage** — ✅ fully wired, ⚠️ partial (with ticket
  reference), ❌ no support
- **Reuse rating**:
  - ★★★ — clean canonical starter, primary pick for its trigger
  - ★★ — usable with caveats (benchmark-specific or knowledge gaps)
  - ★ — scenario-specific; orchestrator should clone-and-replace whole
    subtrees, not just tweak values

## Status of category coverage

| Category | File | Status |
|----------|------|--------|
| Single-phase flow | [examples/single_phase_flow.md](examples/single_phase_flow.md) | ✅ 4 entries |
| CO₂-brine | [examples/co2_brine.md](examples/co2_brine.md) | ✅ 3 entries + decision rule |
| Black oil | [examples/black_oil.md](examples/black_oil.md) | ✅ 1 entry + 3 siblings |
| Dead oil | [examples/dead_oil.md](examples/dead_oil.md) | ✅ 4 entries + 7 siblings |
| Thermal single-phase | [examples/thermal_single_phase.md](examples/thermal_single_phase.md) | ✅ 4 entries + 4 wellbore-geometry siblings |
| Compositional multiphase (generic) | [examples/compositional_multiphase.md](examples/compositional_multiphase.md) | ✅ 4 entries + 6 siblings (incl. Søreide-Whitson sub-family) |
| Wells (cross-cut capability reference) | [examples/wells.md](examples/wells.md) | ✅ patterns reference (format-exception: no entries/ratings — documents well capabilities and routes back to physics files) |
| Immiscible | [examples/immiscible.md](examples/immiscible.md) | ✅ 4 entries + 4 siblings (dedicated `ImmiscibleMultiphaseFlow` solver; cross-refs dead_oil for the buckleyLeverett name clash) |

Tracked under epic agents4geos-3wl, Phase 1 ticket agents4geos-8el.

## Prior art and related tickets

- **Feature-coverage audit**: `docs/knowledge-audit-2026-03-30.md` —
  organized by knowledge module (fluid_models / cross_refs / sanity_rules);
  complementary to this catalog (which is organized by user-facing scenario).
- **agents4geos-npm** — Update the README v0.1 "Supported Physics" table
  (it currently understates schema coverage; this catalog references the
  fuller real set).
- **agents4geos-fot** — Backfilled `fluid_models.py` for `BlackOilFluid` and
  CO₂ Ezrokhi/thermal variants (✅ closed). The "Knowledge-module coverage ⚠️"
  warnings on black_oil and co2_brine entries have been updated accordingly.
- **agents4geos-3wl** — Parent epic.
- **agents4geos-8el** — Phase 1 survey ticket (in progress).

## Out-of-scope (counts, no entries)

The orchestrator should never pick from these directories.

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

Total out-of-scope decks: ~550 of 716 (~77%).
