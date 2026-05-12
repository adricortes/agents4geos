# Compositional multiphase (generic, EOS-based)

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

This category covers **generic equation-of-state compositional** flow —
multi-component hydrocarbon mixtures whose phase split is computed by a
cubic EOS at runtime, as distinct from:

- **CO₂-brine** ([co2_brine.md](co2_brine.md)) — specialized 2-component
  models with prepackaged PVT parameter files.
- **Black oil** ([black_oil.md](black_oil.md)) — 3-phase oil/gas/water with
  tabulated PVT (no EOS at runtime).
- **Dead oil** ([dead_oil.md](dead_oil.md)) — 2- or 3-phase immiscible
  table-driven with no mass transfer.

Generic compositional is the heaviest of these — full flash at every
nonlinear iteration — and is what you reach for when the user's question
involves *which components are present*, *composition changes during
production*, or *mixing of injected and reservoir fluids*.

Source directories (in-scope only):
- `geos/inputFiles/compositionalMultiphaseFlow/` — BC-driven cases including
  the `soreideWhitson/` sub-family.
- `geos/inputFiles/compositionalMultiphaseWell/` — well-driven cases.

## Variant axes

| Axis | Options | When it matters |
|------|---------|----------------|
| **EOS family** | Peng-Robinson (PR), Søreide-Whitson (SW) | PR = workhorse hydrocarbon cubic EOS. SW = brine-aware cubic EOS for water + hydrocarbon equilibrium with salinity effects (use when modelling sour-gas storage in brine, CO₂ + H₂S + brine, or any aqueous-hydrocarbon coexistence). |
| **Flash vs K-value** | Full flash (default) vs pre-tabulated K-values | K-value (`CompositionalTwoPhaseKValueFluid*`) skips the per-iteration flash for cheaper runs at reduced accuracy. Only 1 inputFile uses K-value — avoid unless the user explicitly asks. |
| **Viscosity correlation** | Default (LBC fallback) vs explicit LBC element (`*LohrenzBrayClark`) | The 4 explicit-LBC schema elements have **zero inputFile coverage** — the orchestrator should not propose them as starters. Substitute the non-LBC equivalent and note the deviation. |
| **Component count** | 2-comp / 3-comp / 4-comp / N-comp | 4-component 2-phase is the canonical "generic compositional" exemplar in inputFiles/. More components = more flexibility, much higher cost. |
| **Capillary pressure** | Absent / present (`BrooksCoreyCapillaryPressure`) | Sibling decks with `_cap_` in the name (e.g. `4comp_2ph_cap_1d.xml`) add capillary pressure to the same physics; orchestrator can swap. |
| **Driving** | BC-driven (Box source/sink) vs well-driven (`CompositionalMultiphaseReservoir`) | Same split as elsewhere. |

## Decision rule (stage 2)

- "Generic compositional" / "PR EOS" / "4-component oil-gas":
  → `4comp_2ph_1d` (BC-driven, 1D, academic entry) or
  `compositional_multiphase_wells_2d` (well-driven, 2D, realistic).
- "Add capillary pressure": → switch to the `_cap_1d` sibling
  (`4comp_2ph_cap_1d`), which is `4comp_2ph_1d` with `BrooksCoreyCapillaryPressure`
  appended to the relperm material.
- "Sour gas storage" / "CO₂ + H₂S + brine" / "Søreide-Whitson" / "brine-aware EOS" /
  "salt effects on hydrocarbon solubility":
  → `soreideWhitson/lockExchange/lockExchange_base` (no wells, classical CFD test)
  or `dome_soreide_whitson_base` (well-driven dome reservoir).
- "Lock exchange" by name: → `soreideWhitson/lockExchange/lockExchange_base`.
- "Gravity segregation, compositional": →
  `soreideWhitson/gravSeg/gravSeg.xml` (BC-driven gravity equilibration test
  with the SW EOS).
- Refuse and explain if the user asks for LBC viscosity or K-value: no
  reliable starter exists; substitute the standard variant and warn.

## Entries

### 4comp_2ph_1d — minimal PR EOS, 4-component 2-phase

**File:** `compositionalMultiphaseFlow/4comp_2ph_1d.xml`
**One-liner:** 4-component (typically methane + ethane + propane + butane)
2-phase Peng-Robinson compositional flow in a 1D 10-cell column with Box
source/sink — the smallest possible generic-compositional deck.
**Use as starter when:** the user wants to explore PR-EOS compositional
physics on the simplest possible geometry, build understanding of
component-fraction propagation, or attach new components/BIPs to a deck
without the noise of a full reservoir.

| Tag | Value |
|-----|-------|
| Physics | Compositional 4-component 2-phase, isothermal |
| Solver | Standalone `CompositionalMultiphaseFVM` (no wells), TPFA |
| Fluid | `CompositionalMultiphaseFluid` (PR EOS) — requires componentNames + critical-property arrays + BIPs |
| Relperm | `BrooksCoreyRelativePermeability`, 2-phase |
| Geometry | 1D column, 10 × 1 × 1 m, 10 hex cells |
| Driving | Box-defined source (1 cell at x=0) and sink (1 cell at x=10) |
| Temperature | 297.15 K (24 °C, surface-ish) |
| Initial dt | 1×10⁵ s |
| `targetFlowCFL` | 2 (relatively relaxed, single-phase compressible scaling) |
| Timescale | `maxTime=2×10⁷` s (~231 days) |
| Knowledge-module coverage | ✅ `CompositionalMultiphaseFluid` is on the v0.1 README list (as the generic compositional entry). ⚠️ BIP / critical-property cross-refs not yet sanity-checked. |
| Reuse | ★★★ — primary PR-EOS academic starter |

### compositional_multiphase_wells_2d — PR EOS, well-driven 2D

**File:** `compositionalMultiphaseWell/compositional_multiphase_wells_2d.xml`
**One-liner:** 2D 4-component compositional waterflood with two producers
(BHP-controlled and phase-rate-controlled) and one injector with a custom
4-component injection stream `{0.1, 0.1, 0.1, 0.7}` — the canonical
"well-driven generic compositional" starter.
**Use as starter when:** the user describes any well-driven generic
compositional scenario without naming Søreide-Whitson or CO₂ specifically.
This is also the right starting point for chase-gas / huff-and-puff scenarios
where the injection stream composition differs from the reservoir.

| Tag | Value |
|-----|-------|
| Physics | Compositional 4-component 2-phase (oil, gas), isothermal |
| Solver | `CompositionalMultiphaseReservoir` (couples flow + well), TPFA |
| Fluid | `CompositionalMultiphaseFluid` (PR EOS) |
| Geometry | 2D plate, 15 × 15 × 1 m, 20 × 20 × 1 = 400 cells |
| Driving | 2 producers (one BHP @ 4 MPa target oil rate 1×10⁻³ m³/s, one phaseVolRate with BHP cap 2 MPa), 1 injector (totalVolRate, BHP cap 40 MPa, stream `{0.1, 0.1, 0.1, 0.7}` = heavy in the 4th component) |
| Wells | `InternalWell` inside `InternalMesh`, **polyline geometry** spanning 3 nodes per producer (deviated trajectory) |
| Temperature | 297.15 K |
| Knowledge-module coverage | Same as `4comp_2ph_1d` |
| Reuse | ★★★ — primary well-driven PR-EOS starter |

### soreideWhitson/lockExchange/lockExchange_base — Søreide-Whitson sour-gas + brine

**File:** `compositionalMultiphaseFlow/soreideWhitson/lockExchange/lockExchange_base.xml`
**One-liner:** Lock-exchange test of CH₄ + CO₂ + H₂S + H₂O mixture in a
50 × 50 m vertical slice using the Søreide-Whitson EOS for the brine phase
and Peng-Robinson for the gas phase — the canonical starter for
*water-aware* sour-gas compositional flow.
**Use as starter when:** the user mentions sour gas (H₂S), CO₂ storage with
realistic brine solubility, salt effects on hydrocarbon-water equilibrium,
or asks about the Søreide-Whitson EOS by name. Also the right baseline for
any "classical CFD reference test in a compositional setting" request.

| Tag | Value |
|-----|-------|
| Physics | 4-component (CH₄, CO₂, H₂S, H₂O) 2-phase (oil/brine + gas), isothermal |
| Solver | Standalone `CompositionalMultiphaseFVM` |
| Fluid | `CompositionalTwoPhaseFluidPhillipsBrine` with `equationsOfState="{ SoreideWhitson, PengRobinson }"` (SW for the brine, PR for the gas) |
| EOS tabulation | `pressureCoordinates` × `temperatureCoordinates` grid (13 P levels × 5 T levels, P from 0.1 to 60 MPa, T from 283 to 354 K) |
| BIPs | Explicit 4×4 binary-interaction-parameter matrix, water-to-hydrocarbon entries dominant (CH₄-H₂O = 0.485, CO₂-H₂O = 0.190, H₂S-H₂O = 0.135) |
| Relperm | `TableRelativePermeability` with quadratic Kr curve — note this differs from the BrooksCorey default used elsewhere in compositional decks |
| Geometry | 50 × 1 × 50 m vertical slice (z from −2100 to −2050 m, depth ~2 km), 4 × 1 × 4 cells |
| Driving | Lock-exchange initial condition: distinct compositions on either side of an interface, no flux BCs (gravity-driven mixing) |
| Knowledge-module coverage | ⚠️ `CompositionalTwoPhaseFluidPhillipsBrine` flagged TODO in 2026-03-30 audit; BIP and P-T-grid validation not yet wired. Tracked under agents4geos-fot. |
| Reuse | ★★★ — primary Søreide-Whitson starter |

### dome_soreide_whitson_base — Søreide-Whitson, well-driven dome reservoir

**File:** `compositionalMultiphaseWell/dome_soreide_whitson_base.xml`
**One-liner:** Dome-shaped reservoir with wells, using the Søreide-Whitson
EOS — the only well-driven Søreide-Whitson starter in inputFiles/.
**Use as starter when:** the user wants well-driven sour-gas / brine-aware
compositional flow, or asks to extend the Søreide-Whitson `lockExchange`
toward something with wells. Geometric setup (dome trap) is closer to a
realistic gas-storage / acid-gas-disposal scenario.

| Tag | Value |
|-----|-------|
| Physics | Sour-gas + brine, 4-component, well-driven |
| Solver | `CompositionalMultiphaseReservoir` |
| Fluid | `CompositionalTwoPhaseFluidPhillipsBrine` (same EOS pairing as lockExchange) |
| Knowledge-module coverage | ⚠️ Same as lockExchange |
| Reuse | ★★ — purpose-specific (dome geometry, sour-gas case) but the only SW well exemplar |

## Sibling variants (no separate entries)

- `compositionalMultiphaseFlow/4comp_2ph_cap_1d.xml` — `4comp_2ph_1d` with
  `BrooksCoreyCapillaryPressure` added. Use when the user mentions capillary
  pressure effects in compositional flow.
- `compositionalMultiphaseFlow/initialization_2phase_4comp.xml` — initialization
  test for 2-phase 4-component cases; useful as a reference for how to
  write `HydrostaticEquilibrium`-style initial conditions on PR-EOS systems.
- `compositionalMultiphaseWell/compositional_multiphase_wells_1d.xml` — 1D
  version of the 2D well case; lighter weight, single producer + injector.
- `compositionalMultiphaseWell/resvol_constraint.xml` — adds a *reservoir
  volume constraint* well control; specialized, used when the user wants to
  enforce a target reservoir-volume rate. Don't propose as a default.
- `compositionalMultiphaseFlow/soreideWhitson/1D_100cells/1D_benchmark.xml`
  + `_smoke.xml` — 1D 100-cell SW benchmark (resolution study).
- `compositionalMultiphaseFlow/soreideWhitson/gravSeg/gravSeg.xml` — SW
  gravity-segregation test; companion to the lockExchange.

## What's NOT to propose (and why)

- **LBC viscosity variants** — `CompositionalTwoPhaseFluidLohrenzBrayClark`,
  `CompositionalThreePhaseFluidLohrenzBrayClark`,
  `CompositionalTwoPhaseKValueFluidLohrenzBrayClark`: schema-valid but
  **zero inputFile coverage**. Substitute `CompositionalMultiphaseFluid` or
  `CompositionalTwoPhaseFluid` and tell the user there's no validated
  exemplar to adapt.
- **K-value variants** — `CompositionalTwoPhaseKValueFluidPhillipsBrine`
  has only 1 inputFile use. K-value is a performance optimization (skip
  flash, use tabulated K) at the cost of accuracy. Don't propose as a
  default; mention only when the user is performance-bound.
