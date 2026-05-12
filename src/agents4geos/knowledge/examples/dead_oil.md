# Dead oil

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

`DeadOilFluid` is the most prevalent compositional fluid model in inputFiles/ —
31 total decks, of which 25 are v0.1 in-scope (21 in
`compositionalMultiphaseFlow/`, 4 in `compositionalMultiphaseWell/`). The 6 OUT
cases live in `multiphaseFlowFractures/` (5) and `poromechanics/` (1).

**Naming caveat (important)**: `DeadOilFluid` is really a generic
*"multi-phase immiscible no-mass-transfer fluid container"*. Despite the name,
it shows up modelling CO₂-water systems too — e.g.
`compositionalMultiphaseFlow/benchmarks/buckleyLeverettProblem/buckleyLeverett_base.xml`
uses `phaseNames="{ gas, water }"` with `componentMolarWeight="{ 44e-3, 18e-3 }"`
(CO₂ + water) as an analytical-reference proxy. The orchestrator should NOT
refuse `DeadOilFluid` starters just because the user described a non-oil
scenario.

**Hard external dependency**: every `DeadOilFluid` element references one
`tableFiles` array of PVT data files (`pvdo.txt`, `pvdg.txt`, `pvtw.txt`
patterns) that live next to the XML, usually under a `tables_*/` or `*_table/`
subdirectory. **When the orchestrator clones a dead-oil starter, it MUST also
copy or path-rewrite these tables** — they're not embedded in the XML, and a
missing table file will fail at deck-load time before any sanity check runs.

## Variant axes

- **Phase count**: 2-phase (oil-water OR gas-water) vs 3-phase (oil-gas-water
  with free gas above bubble point). Phase count is set by `phaseNames` and
  must match the component count in `surfaceDensities`, `componentMolarWeight`,
  and `tableFiles`.
- **3-phase relperm interpolation** (when 3-phase only):

  | Filename suffix | Element | When to pick |
  |-----------------|---------|--------------|
  | _(none — default)_ | `BrooksCoreyRelativePermeability` | Corey-style with implicit Stone-I 3-phase interpolation. Default for textbook cases. |
  | `_corey` | Same element, sometimes named explicitly | Same as above; suffix used to disambiguate from Stone/Baker variants in sibling decks. |
  | `_stone2` | `BrooksCoreyStone2RelativePermeability` | When the user mentions Stone-II, intermediate-wet relperm, or asphalt-water systems. |
  | `_baker` | `BrooksCoreyBakerRelativePermeability` | When the user explicitly asks for Baker interpolation. Less common than Stone variants. |

- **Driving**: BC-driven (Box source/sink regions, standalone
  `CompositionalMultiphaseFVM`) vs well-driven (`CompositionalMultiphaseReservoir`
  coupling flow + well).

## Decision rule (stage 2)

- For "waterflood" / "oil + water + gas" / "produce oil while injecting water":
  → 3-phase well-driven, Stone-I default. Start from `dead_oil_wells_2d`;
  scale geometry as needed.
- For a *benchmark-grade* multi-well case: → start from
  `deadOilEgg_base_direct` (Egg benchmark, 12 wells, well-validated in the
  literature).
- For "verify my install / compare to analytical front position":
  → `buckleyLeverett_base` (2-phase, analytical reference, no wells).
- For a *minimal* academic 3-phase case to extend:
  → `deadoil_3ph_corey_1d` (1D, BC-driven, smallest 3-phase entry).
- If the user mentions Stone-II, Baker, or hysteresis: swap the relperm element
  per the variant-axes table above. Stone-II and Baker siblings exist for
  several of the starters — search `compositionalMultiphaseFlow/deadoil_3ph_stone2_1d.xml`,
  `deadoil_3ph_baker_1d.xml`, etc.

## Entries

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
| Knowledge-module coverage | ⚠️ `DeadOilFluid` is in the v0.1 README list but the `tableFiles` cross-ref is flagged TODO in the 2026-03-30 audit — sanity checks may not verify table existence. Tracked in agents4geos-fot. |
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
| Timescale | `maxTime=2e7` s (~231 days); **two-stage event scheduling** (forceDt=1e4 for first 1e5 s, then forceDt=1e5) — orchestrator should preserve this pattern when scaling timescales |
| External artifacts | Colocated PVT tables |
| Knowledge-module coverage | ⚠️ Same `tableFiles` caveat |
| Reuse | ★★★ — academic 3-phase entry point |

## Sibling variants (no separate entries — pick by suffix)

Within `compositionalMultiphaseFlow/` the dead-oil 3-phase 1D family has
prepared variants the orchestrator can swap directly:

- `deadoil_3ph_stone2_1d.xml` — same as `_corey_1d` with Stone-II relperm
- `deadoil_3ph_baker_1d.xml` — same with Baker interpolation
- `deadoil_3ph_staircase_3d.xml` — 3D staircase geometry, same fluid model
- `deadoil_3ph_staircase_hybrid_3d.xml` — same but with `SinglePhaseHybridFVM`-style hybrid FV discretization
- `deadoil_2ph_staircase_gravity_segregation_3d.xml` — 2-phase 3D gravity-segregation test (capillary/buoyancy equilibrium check)
- `grav_seg_1d.xml`, `grav_seg_c1ppu_base.xml`, `grav_seg_base.xml` — gravity-segregation 1D variants (one uses the C1-PPU upwind discretization)
- SPE 10 layer 84/85 benchmark: `benchmarks/SPE10/deadOilSpe10Layers84_85_base_{direct,iterative}.xml` — heterogeneous permeability benchmark
