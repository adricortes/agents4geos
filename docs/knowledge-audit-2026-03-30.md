# Knowledge Base Audit — 2026-03-30

Full audit of GEOS inputFiles/ against Agents4GEOSX knowledge modules.
Based on 4 parallel agent audits covering 200+ input files.

## Status Legend
- [x] Fixed in knowledge base
- [ ] Deferred — documented but not yet implemented

---

## fluid_models.py

- [x] Single-phase + coupled solid (CompressibleSolidConstantPermeability + NullModel + PressurePorosity + ConstantPermeability)
- [x] Compositional + PR EOS (CompositionalMultiphaseFluid)
- [x] CO2BrinePhillipsFluid (with phasePVTParaFiles)
- [x] DeadOilFluid (30+ files, most common compositional fluid — needs tableFiles)
- [x] Thermal coupling pattern (isThermal="1" + ThermalCompressibleSinglePhaseFluid + SolidInternalEnergy + SinglePhaseThermalConductivity)
- [ ] CO2BrineEzrokhiFluid (10 files, same interface as Phillips but different correlations)
- [ ] CompositionalTwoPhaseFluidPhillipsBrine (10 files, Soreide-Whitson EOS, needs tabulated P/T grids)
- [ ] CompressibleSolidCarmanKozenyPermeability (3 files, porosity-dependent perm)
- [ ] CompressibleSolidPressurePermeability (2 files, pressure-dependent perm)
- [ ] ImmiscibleMultiphaseFlow (1 file, TwoPhaseImmiscibleFluid with table-based density/viscosity)

## field_names.py

- [x] SinglePhaseFVM: pressure, temperature
- [x] CompositionalMultiphaseFVM: pressure, globalCompFraction, temperature
- [x] ImmiscibleMultiphaseFlow: pressure, phaseVolumeFraction, temperature
- [x] SourceFlux: NO fieldName attribute; has optional `component` for compositional
- [x] Composition initialization: globalCompFraction with component="0", "1", etc.
- [ ] HydrostaticEquilibrium: special initialization element (17+ files), not a FieldSpecification
- [ ] Aquifer BC: specialized BC type with many parameters (14 files)
- [ ] SinglePhaseReservoir: nests SinglePhaseFVM + SinglePhaseWell

## cross_refs.py

- [x] discretization → NumericalMethods
- [x] targetRegions → ElementRegions
- [x] materialList → Constitutive
- [x] solidModelName, porosityModelName, permeabilityModelName → Constitutive
- [x] solidInternalEnergyModelName → Constitutive (thermal)
- [ ] tableFiles → external .txt files (DeadOilFluid, CO2Brine PVT files)
- [ ] wettingNonWettingRelPermTableNames → Functions (TableRelativePermeability)
- [ ] wettingNonWettingCapPressureTableName → Functions (TableCapillaryPressure)

## sanity_rules.py

- [x] Permeability range (1e-20 to 1e-8 m²)
- [x] Porosity range (0.001 to 0.5)
- [x] Pressure positive
- [x] Temperature range (273-573 K)
- [x] CFL range (0-1)
- [x] Composition sum check (globalCompFraction components must sum to ~1.0)
- [x] materialList must contain a coupled solid (CompressibleSolid* or Porous*)
- [ ] permeabilityComponents must be { x, y, z } triplet
- [ ] DeadOilFluid tableFiles must exist on disk

## Relative Permeability Models

- [x] BrooksCoreyRelativePermeability (80 files, most common)
- [ ] BrooksCoreyBakerRelativePermeability (3 files, 3-phase Baker model)
- [ ] BrooksCoreyStone2RelativePermeability (5 files, 3-phase Stone II)
- [ ] TableRelativePermeability (18 files, table-based)
- [ ] TableRelativePermeabilityHysteresis (10 files, drainage + imbibition)

## Capillary Pressure Models

- [ ] TableCapillaryPressure (18 files, table-based)
- [ ] JFunctionCapillaryPressure (1 file, with surface tension)
- [x] No capillary pressure (most common for simple cases — optional)

## Backlog — New Tools

- [ ] `compute_darcy_velocity(vtk_path, permeability_m2, viscosity_Pa_s)` — compute v = -(k/μ)∇p from pressure field, add as array, save, screenshot
- [ ] `compute_pressure_gradient(vtk_path)` — numerical gradient of pressure field on structured grid

## Mesh Patterns

- [x] InternalMesh with C3D8 (most common)
- [x] Box geometry only (no Cylinder/Sphere in any examples)
- [ ] Multi-region meshes via cellBlockNames partitioning
- [ ] No ExternalMesh in any examples (future feature)

## Event Patterns

- [x] PeriodicEvent with forceDt (fixed timestep)
- [x] PeriodicEvent with timeFrequency (output interval)
- [ ] PeriodicEvent with cycleFrequency (diagnostic output)
- [ ] SoloEvent for one-time initialization
- [ ] maxEventDt, beginTime, endTime attributes

## Solver Parameters

- [ ] NonlinearSolverParameters: newtonTol (1e-6 standard), newtonMaxIter (8-20), lineSearchAction
- [ ] LinearSolverParameters: directParallel="0" (default), gmres+amg for large problems

## materialList Patterns (CONFIRMED across all files)

| Physics | materialList |
|---|---|
| Single-phase flow | { fluid, rock } |
| Single-phase thermal | { fluid, rock, thermalCond } |
| Two-phase immiscible | { fluid, rock, relperm } |
| Compositional multiphase | { fluid, rock, relperm } |
| Compositional + cappres | { fluid, rock, relperm, cappres } |
| Well regions | { fluid } or { fluid, relperm } |
