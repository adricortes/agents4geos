# Immiscible (two-phase, no mass transfer)

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

`TwoPhaseImmiscibleFluid` driven by the **dedicated `ImmiscibleMultiphaseFlow`
solver** — distinct from the compositional family used by every other
multiphase category in this catalog. Source directory:
`geos/inputFiles/immiscibleMultiphaseFlow/` (8 decks total, 4 in-scope base
decks + 4 smoke/benchmark wrappers).

This is the cheapest multiphase physics available — no flash, no mass
transfer, no equation of state — and the right pick when the user wants pure
transport of two non-mixing fluids with tabulated density/viscosity.

## Naming clash with `dead_oil.md`

The catalog has **two `buckleyLeverett_base` entries** in different
categories:

- [`dead_oil.md` → `buckleyLeverett_base`](dead_oil.md) — uses `DeadOilFluid`
  as a CO₂-water analog (component molar weights `{44, 18}` g/mol), routed
  via the compositional solver. The historical implementation.
- **This file → `buckleyLeverett_base`** — uses `TwoPhaseImmiscibleFluid`
  with the dedicated `ImmiscibleMultiphaseFlow` solver. The semantically
  correct immiscible-displacement reference.

Both produce the same analytical front-position solution. The orchestrator
should prefer the immiscible version when the user emphasizes
*"immiscible"* or *"no mass transfer"*, and the dead-oil version when the
user emphasizes *"CO₂-water"* or *"compositional"*.

## Solver / coupling architecture

All in-scope decks use the dedicated solver:

```xml
<Solvers>
  <ImmiscibleMultiphaseFlow
    name="FlowSolver"
    discretization="TPFA"
    targetRegions="{ ... }"
    temperature="300">
    <NonlinearSolverParameters .../>
    <LinearSolverParameters .../>
  </ImmiscibleMultiphaseFlow>
</Solvers>
```

**Wells are NOT supported** by `ImmiscibleMultiphaseFlow` (no `Reservoir`
coupler, no immiscible `*Well` solver in the schema). Every immiscible deck
in inputFiles/ is BC-driven via box-defined source/sink regions. If the user
needs immiscible *with wells*, the orchestrator must route to dead-oil
2-phase (`dead_oil.md`) instead and warn about the substitution.

## Fluid-element subtleties

`TwoPhaseImmiscibleFluid` differs from `DeadOilFluid` / `BlackOilFluid` in
how it gets its PVT:

- **No `tableFiles`** (external files) — uses `densityTableNames` and
  `viscosityTableNames` referencing `<TableFunction>` elements declared
  inside `<Functions>`. The tables must be defined in the same deck (or
  pulled in via `<Included>`), not as external `.txt` files.
- Tables are `pressure → density (kg/m³)` and `pressure → viscosity (Pa·s)`,
  one per phase.
- **No `componentMolarWeight`, no `componentNames`** — immiscible means no
  mass transfer, so molar bookkeeping is moot.

### Phase-naming footgun

The 1D academic deck (`immiscible_2phaseFlow_1d.xml`) declares
`TwoPhaseImmiscibleFluid` with `phaseNames="{water22, gas22}"` (literal
`22`-suffixed names) while the paired `BrooksCoreyRelativePermeability`
declares `phaseNames="{ gas, water }"`. A comment in the deck itself reads:

> `<!-- should probably double check that the phases are defined in the correct order -->`

When adapting an immiscible starter, the orchestrator MUST ensure
`phaseNames` matches *exactly* between the fluid and the relperm element —
both names AND order. This is a real footgun worth filing as a future
sanity-rule (no separate ticket yet — flag if it bites in practice).

## Initial conditions

Immiscible decks initialize **`phaseVolumeFraction`** by `component` index
(NOT `globalCompFraction` like the compositional decks):

```xml
<FieldSpecification name="initialSat1"
  fieldName="phaseVolumeFraction" component="0" scale="1.0"  ... />
<FieldSpecification name="initialSat2"
  fieldName="phaseVolumeFraction" component="1" scale="0.0"  ... />
```

The `component="0"` / `component="1"` indices map to the *order* declared in
`TwoPhaseImmiscibleFluid`'s `phaseNames`. The scale values must sum to 1.0
across the two phases per cell (cellwise saturation conservation).

## Variant axes

| Axis | Options | When it matters |
|------|---------|----------------|
| **Geometry** | 1D academic / 1D Buckley-Leverett / 2D capillary / 2D heterogeneous (SPE 10 layer 84) | Pick by complexity needed |
| **Capillary pressure** | Absent (default) vs `BrooksCoreyCapillaryPressure` added to materialList | The `CapillaryPressure` variant adds Pc(Sw) and demonstrates how immiscible flow + Pc interact |
| **Linear-solver coupling** | direct (fully implicit, default) vs iterative (sequential — only the SPE 10 variant offers both) | direct = robust on small grids; iterative = required for large heterogeneous problems where the direct Jacobian is too expensive |
| **Phase pair** | oil-water (SPE 10, capillary) vs gas-water (Buckley-Leverett, 1D academic) | TwoPhaseImmiscibleFluid is phase-agnostic — name the phases per the engineer's intent and supply matching tables |

## Decision rule (stage 2)

- "1D 2-phase immiscible" / "two-phase no mass transfer" / "simplest
  immiscible starter": → `immiscible_2phaseFlow_1d`.
- "immiscible Buckley-Leverett" / "analytical immiscible front" / "verify
  install with an immiscible reference": → `buckleyLeverett_base`
  (immiscible variant — explicitly disambiguate from
  [dead_oil.md](dead_oil.md)'s same-named entry).
- "immiscible with capillary pressure" / "Pc(Sw) effects in immiscible flow":
  → `immiscibleTwoPhase_CapillaryPressure`.
- "SPE 10 layer 84" / "heterogeneous benchmark" / "real-permeability
  immiscible test": → `immiscibleTwoPhase_SPE10_layer84_base_direct` (or
  `_iterative` sibling for sequential coupling on larger meshes).
- If the user wants wells: refuse, explain, and suggest the dead-oil
  2-phase route ([dead_oil.md](dead_oil.md) → `dead_oil_wells_2d` adapted
  down to 2 phases) as the substitute.

## Entries

### immiscible_2phaseFlow_1d — 1D academic 2-phase immiscible

**File:** `immiscibleMultiphaseFlow/immiscible_2phaseFlow_1d.xml`
**One-liner:** 1D 2-phase immiscible flow in a 10-cell column with Box
source/sink at 4 MPa / 2 MPa pressure BCs — the simplest possible
immiscible starter, intentionally minimal for academic/teaching use.
**Use as starter when:** the user wants the textbook immiscible setup,
wants to attach new features (heterogeneity, gravity, alternative tables)
to a clean base, or needs the smallest immiscible deck for debugging.

| Tag | Value |
|-----|-------|
| Physics | 2-phase immiscible, no mass transfer |
| Solver | `ImmiscibleMultiphaseFlow` (dedicated, NOT compositional) |
| Fluid | `TwoPhaseImmiscibleFluid` with dummy single-point density and viscosity tables (1000 kg/m³, 1 cP for both phases) |
| Phases | `{ water22, gas22 }` ← **note the literal `22`-suffixed names** + warning about phase-naming consistency with relperm |
| Relperm | `BrooksCoreyRelativePermeability`, phase exponents 1.5/1.5, max 0.9/0.9 |
| Geometry | 1D column, 10 × 1 × 1 m, 10 hex cells |
| Driving | Pressure BC at source (4 MPa) and sink (2 MPa); gravity vector `{0, 0, -9.81}` set |
| Temperature | 300 K |
| Timescale | `maxTime=2e3` s (~33 min), `forceDt=100` s |
| Initial conditions | 100% phase 0 (water22), pressure 3 MPa |
| Knowledge-module coverage | ✅ `TwoPhaseImmiscibleFluid` wired in `fluid_models.py` (agents4geos-fot). ⚠️ Phase-naming mismatch between fluid and relperm is a known footgun — not yet sanity-checked. Solver `ImmiscibleMultiphaseFlow` not yet in v0.1 README (agents4geos-npm). |
| Reuse | ★★★ — primary academic immiscible starter |

### buckleyLeverett_base — immiscible analytical reference

**File:** `immiscibleMultiphaseFlow/immiscibleTwoPhase_BuckleyLeverett/buckleyLeverett_base.xml`
**One-liner:** Pure 2-phase immiscible Buckley-Leverett displacement with
the dedicated immiscible solver — the *semantically correct* analytical
reference (compare with [dead_oil.md](dead_oil.md)'s same-named entry,
which uses a `DeadOilFluid` CO₂-water proxy).
**Use as starter when:** the user explicitly wants the immiscible-physics
analytical Buckley-Leverett (front speed, shock front, rarefaction wave),
or when verifying that the `ImmiscibleMultiphaseFlow` solver itself
behaves correctly.

| Tag | Value |
|-----|-------|
| Physics | 2-phase immiscible, no mass transfer |
| Solver | `ImmiscibleMultiphaseFlow` |
| Fluid | `TwoPhaseImmiscibleFluid` with table-function-based density and viscosity |
| Phases | `{ gas, water }` |
| Relperm | `BrooksCoreyRelativePermeability` |
| Geometry | 1D (set by including deck — base meant for inclusion) |
| Driving | Box source / sink |
| Knowledge-module coverage | ✅ As above |
| Reuse | ★★★ — install-sanity for immiscible solver specifically |

### immiscibleTwoPhase_SPE10_layer84_base_direct — heterogeneous SPE 10 benchmark

**File:** `immiscibleMultiphaseFlow/immiscibleTwoPhase_SPE10_layer84/immiscibleTwoPhase_SPE10_layer84_base_direct.xml`
**One-liner:** SPE 10 model 2, layer 84 — the classic heterogeneous-permeability
benchmark — solved as a 2-phase immiscible problem (oil-water) with a
fully-implicit (direct) linear solver. The companion `_iterative` sibling
uses sequential coupling.
**Use as starter when:** the user references SPE 10 by name AND wants
immiscible physics (not compositional / dead-oil), needs a
heterogeneous-permeability benchmark, or wants to compare direct vs
iterative coupling on the same physics.

| Tag | Value |
|-----|-------|
| Physics | 2-phase immiscible, oil-water |
| Solver | `ImmiscibleMultiphaseFlow` with direct linear solver (see `_iterative` sibling for sequential) |
| Fluid | `TwoPhaseImmiscibleFluid` |
| Phases | `{ oil, water }` |
| Geometry | SPE 10 layer 84 heterogeneous-permeability slab (geometry set by including deck) |
| Driving | Box source / sink (SPE 10 standard) |
| Knowledge-module coverage | ✅ As above. SPE 10 cross-references both this entry and the dead-oil SPE 10 entry ([dead_oil.md](dead_oil.md) → `deadOilSpe10Layers84_85_base_*`); pick by physics requirement. |
| Reuse | ★★★ — primary heterogeneous immiscible benchmark |

### immiscibleTwoPhase_CapillaryPressure — capillary-pressure variant

**File:** `immiscibleMultiphaseFlow/immiscibleTwoPhase_CapillaryPressure/immiscibleTwoPhase_CapillaryPressure.xml`
**One-liner:** 2-phase immiscible flow with `BrooksCoreyCapillaryPressure`
added to the material set — demonstrates how Pc(Sw) interacts with
immiscible transport. ATS description: *"Test 2 fluids can mix based on
capillary pressure"* (despite "mix" wording — Pc still respects immiscible
constraint, it modifies the pressure distribution).
**Use as starter when:** the user mentions capillary pressure in an
immiscible context, asks about wettability effects, or wants to extend the
1D academic deck with Pc.

| Tag | Value |
|-----|-------|
| Physics | 2-phase immiscible + capillary pressure |
| Solver | `ImmiscibleMultiphaseFlow` |
| Fluid | `TwoPhaseImmiscibleFluid` |
| Phases | `{ water, gas }` |
| Additional constitutive | `BrooksCoreyCapillaryPressure` (Pc(Sw) added to materialList) |
| Knowledge-module coverage | ✅ Fluid wired. ⚠️ Capillary-pressure models aren't yet in a dedicated `cap_pressure_models.py` (worth filing as follow-up if Pc variants proliferate). |
| Reuse | ★★ — purpose-specific (Pc demonstration) but the only Pc-in-immiscible exemplar |

## Sibling variants (no separate entries)

- `immiscibleTwoPhase_BuckleyLeverett/buckleyLeverett_benchmark.xml` — smoke
  wrapping `buckleyLeverett_base`
- `immiscibleTwoPhase_SPE10_layer84/immiscibleTwoPhase_SPE10_layer84_base_iterative.xml`
  — sequential-coupling sibling of the SPE 10 direct deck
- `immiscibleTwoPhase_SPE10_layer84/immiscibleTwoPhase_SPE10_layer84_benchmark_{direct,iterative}.xml`
  — smoke wrappers for both coupling variants
