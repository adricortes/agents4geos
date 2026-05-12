# Single-phase flow

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

Source directory: `geos/inputFiles/singlePhaseFlow/` (40 decks total). Entries
below are the curated starters; resolution variants (`*_smoke.xml`,
`*_benchmark.xml`) and parameter alternates are noted under sibling sections
rather than getting their own entries.

## Variant axes

- **Compressibility**: incompressible (`compressibility=0`) vs compressible.
- **Dimensionality**: 1D column / 2D slice / 3D box / external-mesh field case.
- **Driving**: Dirichlet pressure BC vs `SourceFlux` (rate-based) vs well-driven
  (see also [wells](wells.md) once that file lands).
- **Thermal coupling**: pure flow vs `isThermal="1"` + `ThermalCompressibleSinglePhaseFluid`
  → covered in [thermal_single_phase.md](thermal_single_phase.md) (TBD).

## Decision rule (stage 2)

- "1D textbook flow" / "simplest possible install check" →
  `incompressible_1d`.
- User describes the driver as a **rate** (kg/s, m³/day) instead of a fixed
  pressure → `sourceFlux_1d`.
- "3D box" / "extend to gravity or heterogeneity" / "base I can wrap with
  Events" → `3D_10x10x10_compressible_base`.
- Field-realistic / external VTK mesh / "looks like real work" →
  `FieldCaseTutorial3_Isothermal_base`.

## Entries

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

## Sibling variants

- `*_smoke.xml` / `*_benchmark.xml` — lean test wrappers that `<Included>` the
  `_base` decks. The orchestrator usually wants the base.
- `compressible_1d.xml`, `compressible_1d_2solids.xml`, `compressible_2d_2fluids.xml`,
  `compressible_2d_2fluids_hybrid.xml` — parameter / geometry alternates of the same
  pattern as `incompressible_1d`.
- `pebi3d_with_properties.vtu` + `incompressible_pebi3d.xml` — alternate
  unstructured polyhedral mesh starter (out of v0.1 scope strictly, since v0.1
  defers unstructured-mesh generation).
- `staircase_3d.xml` — staircase-block geometry, common across categories.
- `polyhedralDiscretizations/` — discretization-method variants (BO and friends);
  the orchestrator should not pick from these unless the user explicitly asks for
  polyhedral.
