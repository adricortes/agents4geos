# Thermal single-phase

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

Source directory: `geos/inputFiles/singlePhaseFlow/` (the same directory as
isothermal single-phase — thermal is the `isThermal="1"` extension, not a
separate physics module). Four inline-`isThermal` base decks exist; all other
thermal files in this directory `<Included>` one of these bases.

## Required constitutive trio

Thermal single-phase needs **three** constitutive models present in the cell
region's `materialList`, in addition to the rock-property models that the
isothermal case already uses:

1. **`ThermalCompressibleSinglePhaseFluid`** — the fluid model. Adds
   `thermalExpansionCoeff`, `specificHeatCapacity`, `referenceInternalEnergy`
   to the standard compressible-fluid params.
2. **`SolidInternalEnergy`** — rock thermal storage. Either *linear*
   (constant `referenceVolumetricHeatCapacity`) or *nonlinear* (with a
   `dVolumetricHeatCapacity_dTemperature` slope term).
3. **`SinglePhaseThermalConductivity`** — rock thermal conduction.
   Either *constant* (`defaultThermalConductivityComponents`) or
   *temperature-dependent* (additional `thermalConductivityGradientComponents`).

The coupled-solid model (e.g. `CompressibleSolidConstantPermeability`) must
reference the `SolidInternalEnergy` via `solidInternalEnergyModelName` for
the solver to wire it in.

## Solver flag rule

`isThermal="1"` must appear on **both** the flow solver and the well solver
when wells are present. Setting it on only one is a silent footgun — the
solver runs, but the energy equation is only enforced on one side of the
flow/well coupling.

## Variant axes

- **Dimensionality**: 2D (`thermalCompressible_2d_base`) / 3D
  (`3D_10x10x10_thermalCompressible_base`) / field-case (`FieldCaseTutorial3_Thermal_base`).
- **Driving**: BC-driven (Box source/sink) vs well-driven
  (`thermalCompressibleWell_base`, the only well-thermal base in the directory).
- **Property dependence on T**: constant vs T-dependent
  thermal-conductivity (linear gradient) vs T-dependent volumetric
  heat-capacity (linear slope).

The 2d_base **ships both linear and nonlinear** versions of `SolidInternalEnergy`
and `SinglePhaseThermalConductivity` in its `Constitutive` block. Sibling decks
that exercise T-dependent properties `<Include>` the 2d_base and simply pick the
nonlinear material name in `materialList`. The orchestrator can do the same
swap when adapting.

## Decision rule (stage 2)

- "2D thermal flow" / "pure thermal convection" / "smallest thermal starter":
  → `thermalCompressible_2d_base`.
- "3D thermal flow demo" / "thermal in a box": →
  `3D_10x10x10_thermalCompressible_base`.
- Well-driven thermal: cold injection / hot injection / wellbore-thermal:
  → `thermalCompressibleWell_base` (uses `SinglePhaseReservoir` to couple
  flow + well; both solvers carry `isThermal="1"`).
- Field-realistic with geothermal gradient / external mesh:
  → `FieldCaseTutorial3_Thermal_base`.
- If the user mentions T-dependent thermal conductivity OR T-dependent heat
  capacity: keep the chosen base, but adapt `materialList` to pick the
  nonlinear material variant. Look at the T-dependent smoke decks
  (`thermalCompressible_temperatureDependentSinglePhaseThermalConductivity_smoke.xml`,
  `thermalCompressible_temperatureDependentVolumetricHeatCapacity_smoke.xml`)
  for the exact materialList swap — both use the `InternalWellbore` mesh,
  so cross-check whether that geometry is what the user actually wants.

## Entries

### thermalCompressible_2d_base — 2D thermal base, BC-driven

**File:** `singlePhaseFlow/thermalCompressible_2d_base.xml`
**One-liner:** 2D thermal compressible flow base deck with `isThermal="1"` on
a `SinglePhaseFVM` solver, shipping both linear and nonlinear thermal-property
variants ready for sibling decks to select via `materialList` — the
canonical 2D thermal starter.
**Use as starter when:** the user asks for any 2D thermal flow problem, or
wants the smallest base that exposes T-dependent material variants.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, compressible, thermal (`isThermal="1"`) |
| Solver | `SinglePhaseFVM` (TPFA), no wells |
| Fluid | `ThermalCompressibleSinglePhaseFluid` (1000 kg/m³, 1 cP, thermal-expansion 3×10⁻⁴ 1/K) |
| Rock thermal storage | Two `SolidInternalEnergy` variants pre-defined: `rockInternalEnergy_linear` (constant Cv = 1×10⁶ J/m³/K) and `rockInternalEnergy_nonLinear` (Cv = 4.56×10⁶ + 1×10⁶·T J/m³/K) |
| Rock thermal conductivity | Two `SinglePhaseThermalConductivity` variants pre-defined: `thermalCond_linear` (constant 1.66 W/m/K isotropic) and `thermalCond_nonLinear` (1.5 + −12×10⁻⁴·(T−20) W/m/K) |
| Coupled solid | Two `CompressibleSolidConstantPermeability` instances: `rock_linear` and `rock_temperatureDependentVolumetricHeatCapacity` — both with `solidInternalEnergyModelName` set to the matching `SolidInternalEnergy` |
| Geometry | Set by including deck (base for inclusion) |
| Mesh / driving | Set by including deck — typically `InternalMesh` 2D with Box source/sink |
| Reference temperature | 0 (units arbitrary in this base; sibling decks scale) |
| Knowledge-module coverage | ✅ Thermal trio appears in v0.1 supported-physics. ⚠️ The T-dependent gradient/slope parameters aren't separately documented; sanity-rules for temperature range still apply. |
| Reuse | ★★★ — primary 2D thermal starter |

### 3D_10x10x10_thermalCompressible_base — 3D thermal base

**File:** `singlePhaseFlow/3D_10x10x10_thermalCompressible_base.xml`
**One-liner:** 3D extension of the 2D thermal base — same constitutive trio,
extended to a structured cube. Companion to the isothermal
`3D_10x10x10_compressible_base` from [single_phase_flow.md](single_phase_flow.md).
**Use as starter when:** the user asks for 3D thermal flow demo, or wants to
extend the isothermal 3D box with thermal physics. Pair with
`3D_10x10x10_thermalCompressible_smoke.xml` for a runnable case.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, compressible, thermal |
| Solver | `SinglePhaseFVM`, no wells |
| Constitutive | Same trio as 2d_base (fluid + SolidInternalEnergy + SinglePhaseThermalConductivity) |
| Geometry | 3D cube, 10 × 10 × 10 m |
| Mesh | `InternalMesh`, set by including deck |
| Reuse | ★★★ — primary 3D thermal starter |

### thermalCompressibleWell_base — well-driven thermal (injector)

**File:** `singlePhaseFlow/thermalCompressibleWell_base.xml`
**One-liner:** Single-phase water injector at 323 K (50 °C) into a 353 K
(80 °C) reservoir under BHP control, both flow and well solvers carrying
`isThermal="1"` — the cold-injection wellbore-thermal starter.
**Use as starter when:** the user describes cold-water injection / hot-water
injection / any thermal scenario where a *well* is the temperature source or
sink. This is also the right starting point when adapting toward J-T cooling
or geothermal-loop scenarios.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, compressible, thermal, well-coupled |
| Solver | `SinglePhaseReservoir` (couples) + `SinglePhaseFVM` (`isThermal="1"`) + `SinglePhaseWell` (`isThermal="1"`) |
| Driving | One injector, `control="BHP"`, target BHP 14.5 MPa, `injectionTemperature="323"` (50 °C), `injectionStream="{1.0, 0.0}"` |
| Reservoir temperature | 353 K (80 °C) initial |
| Surface conditions | 14.5 MPa, 300.15 K — note the surface pressure here equals the BHP target (unusual; benchmark-specific choice) |
| Geometry | Box-defined source/sink corners (10 × 10 × 10 m source at low corner, sink at high corner) |
| Constitutive | Same thermal trio as 2d_base |
| Initial dt | 1 000 s |
| Coupling tolerances | `newtonTol="1.0e-3"` (loose, well-coupling is non-linear), `maxTimeStepCuts="10"` — pre-tuned for well-thermal robustness |
| Knowledge-module coverage | ⚠️ The dual-solver `isThermal="1"` rule isn't yet a sanity check — wiring it asymmetrically passes schema but breaks physics |
| Reuse | ★★★ — the only well-thermal base in this directory |

### FieldCaseTutorial3_Thermal_base — field case with geothermal gradient

**File:** `singlePhaseFlow/FieldCaseTutorial3_Thermal_base.xml`
**One-liner:** 3D thermal single-phase flow on the FieldCaseTutorial3
synthetic reservoir mesh, with a geothermal temperature gradient applied as
the initial condition — the "thermal version of the field case" extension.
**Use as starter when:** the user references an external VTK mesh AND wants
thermal physics, mentions a geothermal gradient, or asks to extend the
isothermal `FieldCaseTutorial3` (see
[single_phase_flow.md](single_phase_flow.md)) with energy transport.

| Tag | Value |
|-----|-------|
| Physics | Single-phase, compressible, thermal |
| Solver | `SinglePhaseFVM` (`isThermal="1"`) |
| Mesh | `VTKMesh` (synthetic reservoir geometry, same as isothermal sibling) |
| Initial T | Geothermal gradient (depth-dependent — see paired `_smoke.xml` for exact gradient and BC wiring) |
| Constitutive | Thermal trio |
| Reuse | ★★★ — the field-realistic thermal extension |

## Sibling variants (no separate entries — pick by include + materialList swap)

All wellbore-geometry, `<Include>` `thermalCompressible_2d_base.xml`, and
differ only in which material variant they pick:

- `thermalCompressible_temperatureDependentSinglePhaseThermalConductivity_smoke.xml`
  / `_benchmark.xml` — uses `thermalCond_nonLinear` in materialList,
  `InternalWellbore` cylindrical mesh (radii 0.1, 0.106, 0.133, 1.0 m, 90°
  azimuthal slice). Use when modelling near-wellbore radial flow with
  T-dependent thermal conductivity.
- `thermalCompressible_temperatureDependentVolumetricHeatCapacity_smoke.xml`
  / `_benchmark.xml` — uses `rock_temperatureDependentVolumetricHeatCapacity`,
  same wellbore mesh. Use for T-dependent heat capacity.

Also in the directory:
- `thermalCompressibleWell.xml` — runnable smoke wrapping `thermalCompressibleWell_base`.
- `thermalCompressible_2d_smoke.xml` / `_benchmark.xml` — runnable smokes wrapping
  the 2d base; "Pure thermal convection problem (2D, compressible, Dirichlet BC)"
  per ATS.
