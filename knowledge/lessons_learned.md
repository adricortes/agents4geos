# GEOS Runtime Lessons Learned

Read this file BEFORE choosing solver/constitutive combinations or setting up
FieldSpecifications. Each lesson documents a real runtime failure and the
correct pattern to avoid it.

---

## Solver-Constitutive Compatibility

### ImmiscibleMultiphaseFlow requires TwoPhaseImmiscibleFluid
- **Wrong:** Using `InvariantImmiscibleFluid` — different C++ class, not found by `dynamic_cast`
- **Right:** `TwoPhaseImmiscibleFluid` with `TableFunction` references for density/viscosity per phase
- **Pattern:**
  ```xml
  <TwoPhaseImmiscibleFluid name="fluid"
    phaseNames="{ gas, water }"
    densityTableNames="{ gasDensityTable, waterDensityTable }"
    viscosityTableNames="{ gasViscosityTable, waterViscosityTable }"/>
  ```
- **Source:** Runtime error — `constitutive model not found` in `ImmiscibleMultiphaseFlow`

### Every CellElementRegion materialList must include a coupled solid
- **Wrong:** `materialList="{ fluid, relperm }"` — missing coupled solid
- **Right:** Always include a `CompressibleSolidConstantPermeability` (or similar) in `materialList`
- **Pattern:**
  ```xml
  <CellElementRegion name="Domain"
    cellBlocks="{ cb1 }"
    materialList="{ fluid, rock, relperm }"/>

  <CompressibleSolidConstantPermeability name="rock"
    solidModelName="nullSolid"
    porosityModelName="rockPorosity"
    permeabilityModelName="rockPerm"/>
  ```
- **Source:** Runtime error — `coupled solid constitutive model not found`

## FieldSpecification Rules

### ImmiscibleMultiphaseFlow uses phaseVolumeFraction, not globalCompFraction
- **Wrong:** Setting `fieldName="globalCompFraction"` with `ImmiscibleMultiphaseFlow`
- **Right:** Use `fieldName="phaseVolumeFraction"` — immiscible solver tracks phase volumes, not component moles
- **Pattern:**
  ```xml
  <FieldSpecification name="initialGasSaturation"
    fieldName="phaseVolumeFraction"
    component="0"
    initialCondition="1"
    setNames="{ all }"
    scale="0.5"/>
  ```
- **Source:** Runtime error — field `globalCompFraction` not found on `ImmiscibleMultiphaseFlow`

### Component fractions must sum to 1.0 per region
- **Wrong:** Setting `globalCompFraction` for only one component, or fractions that don't sum to 1
- **Right:** One `FieldSpecification` per component, with `scale` values summing to 1.0 on each `setNames` group
- **Pattern:**
  ```xml
  <FieldSpecification name="initComp_co2" fieldName="globalCompFraction"
    component="0" initialCondition="1" setNames="{ all }" scale="0.1"/>
  <FieldSpecification name="initComp_water" fieldName="globalCompFraction"
    component="1" initialCondition="1" setNames="{ all }" scale="0.9"/>
  ```
- **Source:** Runtime error — `component fractions do not sum to 1`

## Mesh and Geometry Rules

### Geometry box must enclose cell centers, not just boundaries
- **Wrong:** A `Box` geometry with `xMax` exactly at the mesh boundary — misses cell centers
- **Right:** Extend the box by half a cell width past the boundary to capture cell centers
- **Pattern:**
  ```xml
  <!-- For a mesh with dx=10m and xMax=100m, use xMax=105 to capture the last column -->
  <Box name="rightFace" xMin="{ 95, -1, -1 }" xMax="{ 105, 1001, 1001 }"/>
  ```
- **Source:** Runtime error — `targets empty set` (geometry box doesn't enclose cell centers)

## NumericalMethods Rules

(No runtime lessons yet — add here as discovered.)
