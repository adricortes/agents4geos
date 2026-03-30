# Example: Single-Phase Flow Simulation

## User
> Set up a single-phase water flow through a 1km x 1km x 100m box. Injection on the left face at 1e-5 kg/s, pressure outlet on the right at 10 MPa. Run for 10,000 seconds, output VTK every 1,000 seconds.

## Agent Workflow

1. **Recommend model**: `recommend_fluid_model("single phase water flow")` → SinglePhaseFVM + CompressibleSinglePhaseFluid

2. **Create document**: `create_document()` → doc_id

3. **Add solver**: `add_element(doc_id, "Solvers", "SinglePhaseFVM", "flow", {discretization: "fluidTPFA", targetRegions: "{ Domain }"})`

4. **Add mesh**: `add_element(doc_id, "Mesh", "InternalMesh", "mesh1", {elementTypes: "{ C3D8 }", nx: "{ 50 }", ny: "{ 50 }", nz: "{ 10 }", ...})`

5. **Add constitutive**: CompressibleSinglePhaseFluid with density=1000, viscosity=0.001, compressibility=4.4e-10

6. **Add element region**: CellElementRegion "Domain" with materialList="{ water }"

7. **Add geometry boxes**: "left_face" and "right_face" for BC application

8. **Add BCs**: FieldSpecification for injection (SourceFlux) and outlet (pressure Dirichlet)

9. **Add events**: PeriodicEvent for solver (dt=100s) and outputs (every 1000s), maxTime=10000

10. **Validate**: `validate_cross_references` + `sanity_check` + `preview_xml`

11. **Save**: `save_xml(doc_id, "single_phase_flow.xml")` → auto-validates with xmllint
