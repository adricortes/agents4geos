# Wells — cross-cutting capability reference

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, and the top-level category router.

**This file is a format exception.** Unlike the per-physics detail files
(single_phase_flow.md, co2_brine.md, dead_oil.md, …), this file does not
contain "entries" with ★ ratings. Every well-driven example *already* lives
in its physics file — there's no separate "wells starter deck" to clone.
What this file documents is the **well patterns themselves**: which XML
attributes exist, how they combine, and which deck demonstrates each
pattern in action. Consult this file when the user asks a *well-shaped
question* ("how do I control by mass rate?", "can I do a deviated
trajectory?", "do I need surface conditions?") that cuts across physics
categories.

## A. Solver wiring — what wraps what

The flow-only standalone case has no `*Reservoir` wrapper and no `*Well`
solver. Adding wells requires three coupled solver elements: the
`*Reservoir` coupler, the standard flow solver, and the matching
`*Well` solver. Both single-phase and compositional follow the same
pattern.

| Wiring | When | Example deck |
|--------|------|--------------|
| Standalone `SinglePhaseFVM` (no wells) | BC-driven only | `incompressible_1d`, `3D_10x10x10_compressible_base` ([single_phase_flow.md](single_phase_flow.md)) |
| Standalone `CompositionalMultiphaseFVM` (no wells) | BC-driven compositional | `4comp_2ph_1d` ([compositional_multiphase.md](compositional_multiphase.md)), `co2_thermal_2d` ([co2_brine.md](co2_brine.md)), `buckleyLeverett_base` ([dead_oil.md](dead_oil.md)) |
| `SinglePhaseReservoir` → `SinglePhaseFVM` + `SinglePhaseWell` | Single-phase wells (typically thermal) | `thermalCompressibleWell_base` ([thermal_single_phase.md](thermal_single_phase.md)) |
| `CompositionalMultiphaseReservoir` → `CompositionalMultiphaseFVM` + `CompositionalMultiphaseWell` | All compositional wells (CO₂, black oil, dead oil, PR-EOS, Søreide-Whitson) | `simpleCo2InjTutorial_base`, `dead_oil_wells_2d`, `deadOilEgg_base_direct`, `black_oil_wells_saturated_3d`, `compositional_multiphase_wells_2d` |

The wrapper's `targetRegions` must include both the reservoir region(s)
and every `wellRegion*` — wells live in their own element regions, declared
by `<WellElementRegion>` and populated by `<InternalWell>` elements inside
the mesh.

## B. Well type

| Type | XML | Stream attribute | Sign convention |
|------|-----|------------------|-----------------|
| Injector | `type="injector"` | `injectionStream="{ ... }"` (mole fractions summing to 1, length = number of components) | flow INTO reservoir |
| Producer | `type="producer"` | `targetPhaseName="oil"` (or `"gas"`, `"water"`) — names the phase the rate target refers to | flow OUT of reservoir |

A given well solver can hold multiple `<WellControls>` elements (each with
its own `name` and `type`); the deck activates one by referencing its name
elsewhere (or by being included via a wrapping smoke deck). Examples like
`class09_pb3_drainageOnly_iterative_base` ship with 3 pre-wired controls
ready to be selected.

## C. Control modes — the main matrix

The control mode chooses *what the solver targets*. Most rate-mode wells
also carry a `targetBHP` as a **cap** — the solver enforces the rate while
respecting the BHP limit. The orchestrator should always supply both for
rate controls.

| `control="..."` | Required | Optional / common | When to pick | Demo deck |
|-----------------|----------|-------------------|--------------|-----------|
| `BHP` | `targetBHP` | — | Pressure-limited well; classical waterflood; depletion drive | `deadOilEgg_base_direct` (all 12), `black_oil_wells_saturated_3d` (both wells) |
| `totalVolRate` | `targetTotalRate`, `targetBHP` (cap) | `useSurfaceConditions="1"` + surface P,T | Volumetric injection at known rate (m³/s) | `simpleCo2InjTutorial_base`, `dead_oil_wells_2d` (injector) |
| `phaseVolRate` | `targetPhaseRate`, `targetPhaseName`, `targetBHP` (cap) | surface P,T | Targeted oil/gas/water rate on a producer | `dead_oil_wells_2d` (producer #2) |
| `massRate` | `targetMassRate`, `targetBHP` (cap) | surface P,T | CO₂ mass-rate injection (industry-standard for storage projects) | `class09_pb3_drainageOnly_iterative_base` (`MAX_MASS_INJ`) |
| `*TableName` variants — `targetBHPTableName`, `targetTotalRateTableName`, `targetMassRateTableName`, `targetPhaseRateTableName` | matching `<TableFunction>` defined under `Functions` | as above | Time-varying control schedule (shut-in/ramp-up periods, history match) | `class09_pb3_*` (`MAX_MASS_INJ_TABLE`, `totalRateTable`), `dead_oil_wells_2d` (producer #1: `BHPTable`) |

The table-controlled variants reference a `<TableFunction>` in the
`<Functions>` block — the table file (or inline values) provides the
time-dependent schedule. The orchestrator must remember to also adapt the
table when scaling the timescale.

## D. Surface conditions

Setting `useSurfaceConditions="1"` makes the well's `targetTotalRate` /
`targetMassRate` / `targetPhaseRate` refer to **surface conditions** rather
than downhole. When set, the deck must also supply `surfacePressure` and
`surfaceTemperature`.

- **Standard surface conditions**: 101 325 Pa, 288.71 K (15 °C). All
  CO₂-brine starters use exactly these — see `simpleCo2InjTutorial_base`,
  `class09_pb3_*`.
- **Non-standard surface conditions**: some dead-oil decks use the *reservoir*
  temperature as the surface reference (e.g. `dead_oil_wells_2d` uses
  297.15 K for both reservoir and "surface") — this is a benchmark-style
  simplification, not realistic. The orchestrator should flag this when
  adapting toward realistic operating conditions.
- **Downhole rates**: omit `useSurfaceConditions` (or set to `"0"`). All
  black-oil starters operate this way — rates are downhole volumes.

**Pick rule**: if the user phrases rates in surface units (sm³/d, sm³/h,
bbl/d, kg/s referenced to STP), set `useSurfaceConditions="1"` with
standard P,T. If they phrase rates in reservoir/downhole terms, leave it
unset. When adapting a starter, the orchestrator must convert the user's
units accordingly — don't change the rate number without changing the flag.

## E. Trajectory and perforation

Wells live inside `<InternalMesh>` as `<InternalWell>` elements, with a
polyline trajectory and one or more perforations.

### Vertical (single-segment, single-perforation)

The simplest pattern — two polyline nodes, one segment, one perforation
located by a length along the well. Example: `black_oil_wells_saturated_3d`,
`compositional_multiphase_wells_1d`:

```xml
<InternalWell ...
  polylineNodeCoords="{ { 5.0, 5.0, 2.0 },
                        { 5.0, 5.0, 0.0 } }"
  polylineSegmentConn="{ { 0, 1 } }"
  radius="0.1"
  numElementsPerSegment="1">
  <Perforation name="perf1" distanceFromHead="1.00"/>
</InternalWell>
```

### Deviated (multi-segment polyline)

Multi-node polyline, multiple segments connecting consecutive node
indices, often multiple perforations. Example:
`compositional_multiphase_wells_2d` producers span 3 nodes (head → middle →
toe) for a deviated trajectory across a 2D plate. The `polylineSegmentConn`
array enumerates the `(i, i+1)` connections explicitly.

### Perforation alternatives

- `distanceFromHead="X"` — locate the perforation at length X along the
  well from the head. Numerically simple, robust for non-aligned meshes.
- `setNames="{ X }"` — perforate every cell in the named geometric set X.
  Useful when you have a `Geometry/Box` already defining the completion
  interval.

The two forms are mutually exclusive on a single `<Perforation>` element.

## F. Thermal wells

Thermal coupling adds two requirements (also covered in
[thermal_single_phase.md](thermal_single_phase.md), repeated here for
discoverability):

1. **`isThermal="1"` must appear on both the flow solver AND the well
   solver.** Setting it on only one side is a silent footgun — the deck
   loads, the run completes, but the energy equation is only enforced on
   one side of the flow/well coupling and the result is physically
   incorrect.
2. **`injectionTemperature` on `<WellControls>`** for injectors —
   `thermalCompressibleWell_base` shows 323 K (50 °C) cold injection into
   a 353 K (80 °C) reservoir.

No additional thermal-specific control modes — BHP, rate, table all work.

## G. Cross-flow control

`enableCrossflow="0"` blocks reverse flow through the perforations during
the simulation. Set to `"0"` (blocked) for:

- Storage / pure-injection scenarios where back-flow is non-physical
  (every CO₂-brine injector sets this).
- Injectors that should never accidentally produce.

Leave at the default (permissive) for:

- Production wells where back-flow can be physical (transient pressure
  swings, gas coning).
- Black-oil and dead-oil starters generally don't set it.

## H. Specialized / rarely-used controls (anti-patterns)

- `resvol_constraint.xml` — reservoir-volume-rate constraint, only one
  inputFile use. Don't propose unless the user explicitly asks for
  reservoir-volume targeting.

If more 1-use specialized controls surface from later catalog work, list
them here.

## I. Cross-reference back to physics files

For specific well-driven deck details, the orchestrator should always
read the matching physics file:

| For physics… | …see |
|--------------|------|
| CO₂-brine wells (Phillips, Ezrokhi, thermal) | [co2_brine.md](co2_brine.md) |
| Black-oil wells (saturated / unsaturated, Stone I/II) | [black_oil.md](black_oil.md) |
| Dead-oil wells (2-phase / 3-phase, Egg, SPE 10) | [dead_oil.md](dead_oil.md) |
| PR-EOS / Søreide-Whitson wells | [compositional_multiphase.md](compositional_multiphase.md) |
| Single-phase thermal wells (cold/hot injection) | [thermal_single_phase.md](thermal_single_phase.md) |
