# Example: CO2 Injection into Saline Aquifer

## User
> I need a CO2 injection simulation into a saline aquifer at 2km depth. 1km x 1km domain, 100m thick. Inject 10 kg/s CO2 from a well at the center. Monitor pressure and saturation for 30 years.

## Agent Workflow

1. **Recommend model**: `recommend_fluid_model("CO2 injection into saline aquifer")` → CompositionalMultiphaseFVM + CO2BrinePhillipsFluid

2. **Compute fluid properties**: `compute_brine_properties(pressure_Pa=2e7, temperature_K=350, salinity_wt_pct=10)` → density ~1050 kg/m3, viscosity ~3.5e-4 Pa.s

3. **Generate rel perm**: `generate_rel_perm(model="BrooksCorey", swc=0.15, sorg=0.05, exponents={nw: 4, no: 2})` → table for BrooksCoreyRelativePermeability

4. **Create document**: `create_document()` → doc_id

5. **Add solver**: CompositionalMultiphaseFVM with 2-component (CO2 + H2O), 2-phase

6. **Add mesh**: InternalMesh 50x50x10, 20m x 20m x 10m cells

7. **Add constitutive models**:
   - CO2BrinePhillipsFluid
   - BrooksCoreyRelativePermeability (with computed parameters)
   - ConstantPermeability (1e-13 m^2)
   - BiotPorosity (0.2)

8. **Add BCs**: Injection well at center (10 kg/s CO2), hydrostatic pressure boundaries

9. **Add events**: maxTime = 9.46e8 s (30 years), output every 3.15e7 s (1 year)

10. **Validate and save**
