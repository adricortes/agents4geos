# Example: Edit an Existing XML File

## User
> Open my_sim.xml and double the injection rate, change the output frequency to every 500 seconds, and add a temperature initial condition of 350 K.

## Agent Workflow

1. **Load**: `load_xml("my_sim.xml")` → doc_id, shows sections and element count

2. **Find injection rate**: `preview_xml(doc_id, section="FieldSpecifications")` → find the SourceFlux element

3. **Update rate**: `update_element(doc_id, "FieldSpecifications/SourceFlux[@name='injection']", {scale: "2e-5"})` (doubled from 1e-5)

4. **Update output frequency**: `update_element(doc_id, "Events/PeriodicEvent[@name='outputs']", {timeFrequency: "500"})`

5. **Add temperature IC**: `add_element(doc_id, "FieldSpecifications", "FieldSpecification", "temperatureIC", {fieldName: "temperature", initialCondition: "1", setNames: "{ all }", scale: "350"})`

6. **Validate**: `validate_cross_references(doc_id)` — check "all" exists in Geometry

7. **Diff**: `diff_xml("my_sim.xml", "my_sim_updated.xml")` — show what changed

8. **Save**: `save_xml(doc_id, "my_sim_updated.xml")`
