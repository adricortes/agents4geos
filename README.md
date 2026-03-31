# Agents4GEOSX

Natural language interface for creating and editing [GEOS](https://github.com/GEOS-DEV/GEOS) simulation input files, built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) MCP server with skills, slash commands, and hooks.

Instead of writing 200-500 lines of cross-referenced XML by hand, describe your simulation in plain English and let the agent assemble validated XML using structured tools backed by real physics computations.

## Architecture

```
User Layer        /geos create... | /geos:edit | /geos:validate | Natural language
                                    |
Agent Layer       Orchestrator skill + 10 slash commands + auto-validation hooks
                                    |  (MCP Protocol)
Tool Layer        FastMCP Server — 46 tools in 5 groups
                  Schema (7) | Fluids (10) | Mesh (8) | XML (13) | PostProc (8)
                                    |
Data Layer        schema.xsd | GEOS inputFiles/ | PVT tables | VTK outputs
```

### Tool Groups

| Group | Tools | Powered By | Purpose |
|-------|-------|------------|---------|
| **Schema & Introspection** | 7 | geos-tui schema parser | Query elements, attributes, types, cross-references |
| **Fluid & Constitutive** | 10 | pyResToolbox (SI units) | Gas/oil/brine PVT, rel perm (model + table), cap pressure, well IPR |
| **Mesh** | 8 | PyVista | Create/load meshes, statistics, headless screenshots, XML generation |
| **XML Assembly & Validation** | 13 | geos-tui XML R/W + xmllint | Create/load/edit/save documents, validate cross-refs, templates, geometry boxes |
| **Post-Processing** | 8 | PyVista + pyResToolbox | VTK output analysis, field screenshots, Darcy velocity, material balance |

### Knowledge Base

Constitutive assembly patterns learned from auditing 200+ official GEOS input files:

- **Coupled solid pattern**: `materialList` references the coupled solid (e.g., `CompressibleSolidConstantPermeability`), never individual sub-models
- **Solver → field name mapping**: Which `fieldName` values are valid for each solver type
- **Cross-reference graph**: Which attributes reference which sections
- **Physics sanity rules**: Permeability range, porosity, pressure, temperature, composition sum
- **NL → model recommender**: Maps keywords ("CO2 injection", "dead oil") to solver + constitutive assembly

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- `xmllint` (for schema validation)
- GEOS build with `schema.xsd` (for schema parsing)

### Editable Dependencies

These repositories must be available locally:

| Dependency | Path (relative to this repo) | What it provides |
|------------|------------------------------|------------------|
| [geos-tui](https://github.com/adricortes/geos-tui) | `../../geos-tui` (`~/geos-tui`) | Schema parser, XML reader/writer, templates, validation |
| [pyResToolbox](https://github.com/adricortes/pyResToolbox) (SI fork) | `../pyResToolbox` (`~/codes/pyResToolbox`) | Fluid PVT, relative permeability, well performance. Fork of [mwburgoyne/pyResToolbox](https://github.com/mwburgoyne/pyResToolbox) with comprehensive SI unit refactoring. |
| [PyVista](https://github.com/pyvista/pyvista) | `../pyvista` (`~/codes/pyvista`) | Mesh creation, VTK I/O, headless visualization |

## Installation

### 1. Clone and install

```bash
cd ~/codes
git clone git@github.com:adricortes/agents4geosx.git
cd agents4geosx
uv sync --all-extras
```

### 2. Verify dependencies

```bash
uv run python -c "from geos_tui.schema.parser import SchemaParser; print('geos-tui OK')"
uv run python -c "from pyrestoolbox import gas; print('pyResToolbox OK')"
uv run python -c "import pyvista as pv; print('PyVista OK')"
```

### 3. Set up a workspace

Create a separate directory for testing/using the agent:

```bash
mkdir -p ~/codes/agents4geosx-workspace
cd ~/codes/agents4geosx-workspace

# Symlink your GEOS build
ln -s /path/to/GEOS geos

# Deploy slash commands
mkdir -p .claude/commands
cp ~/codes/agents4geosx/skills/*.md .claude/commands/

# Register the MCP server
claude mcp add agents4geosx -- \
  env GEOS_SCHEMA=$(pwd)/geos/build/schema.xsd \
  uv run --directory ~/codes/agents4geosx \
  python -m agents4geosx
```

### 4. Auto-approve MCP tools (optional)

To avoid confirming every tool call during use:

```bash
cat > .claude/settings.local.json << 'EOF'
{
  "permissions": {
    "allow": [
      "mcp__agents4geosx__*",
      "Read",
      "Glob",
      "Grep"
    ]
  }
}
EOF
```

### 5. Start Claude Code

```bash
cd ~/codes/agents4geosx-workspace
claude
```

## Usage

### Create a simulation from natural language

```
/geos create a single-phase water flow simulation: 500m x 500m x 50m domain,
constant permeability 1e-13 m2, injection on the left face at 1e-4 kg/s,
pressure outlet on the right at 20 MPa, run for 1 year with VTK output monthly
```

### Edit an existing XML file

```
/geos:edit my_sim.xml — double the injection rate and refine the mesh to 50x50x10
```

### Query the schema

```
/geos:schema what solvers are available?
/geos:schema describe SinglePhaseFVM — what are its essential attributes?
```

### Compute fluid properties

```
/geos:fluids compute brine properties at 30 MPa, 350 K, 10% salinity
```

### Validate an XML file

```
/geos:validate my_sim.xml
```

### Run a GEOS simulation and analyze output

```
/geos:run validate and run single_phase_flow.xml, then show me the pressure field
```

### Analyze GEOS output

```
/geos:postprocess read the VTK output in run/ — list available fields and show pressure
```

### All slash commands

| Command | Purpose |
|---------|---------|
| `/geos` | Main entry — create, edit, or query simulations |
| `/geos:edit` | Edit an existing XML file |
| `/geos:validate` | Validate XML (schema + cross-refs + physics sanity) |
| `/geos:inspect` | Describe what an XML file contains |
| `/geos:mesh` | Create or visualize meshes |
| `/geos:fluids` | Compute fluid PVT properties |
| `/geos:relperm` | Generate relative permeability curves |
| `/geos:postprocess` | Analyze GEOS VTK output |
| `/geos:schema` | Query the GEOS XSD schema |
| `/geos:run` | Run GEOS simulation and analyze output |

## MCP Tools Reference

### Schema & Introspection (7)

| Tool | Purpose |
|------|---------|
| `list_sections` | Top-level XML sections |
| `list_elements` | Elements in a section (v1 scope filter) |
| `describe_element` | Full element details: attributes, children, description |
| `list_attributes` | Attributes filtered by group (essential/physics/advanced) |
| `get_type_info` | Type constraints, patterns, enums |
| `lookup_field_names` | Valid BC/IC field names per solver type |
| `get_cross_references` | What other sections an element's attributes reference |

### Fluid & Constitutive (10)

| Tool | Purpose |
|------|---------|
| `compute_gas_properties` | Z-factor, density, viscosity, Bg, Cg (SI) |
| `compute_oil_properties` | Pb, Rs, Bo, density, viscosity (SI) |
| `compute_brine_properties` | Density, viscosity, Bw (SI) |
| `generate_pvt_table` | Full PVT table over pressure range |
| `generate_rel_perm` | Brooks-Corey / VanGenuchten / LET relative permeability |
| `create_table_rel_perm_xml` | Generate TableRelativePermeability + TableFunction XML from user data |
| `fit_rel_perm` | Fit relperm model to measured data |
| `generate_cap_pressure` | Brooks-Corey / VanGenuchten capillary pressure curve |
| `compute_well_ipr` | Well inflow performance (radial flow) |
| `recommend_fluid_model` | NL description → solver + full constitutive assembly |

### Mesh (8)

| Tool | Purpose |
|------|---------|
| `create_structured_mesh` | Uniform grid, saves VTK |
| `create_rectilinear_mesh` | Variable-spacing grid |
| `load_mesh` | Inspect existing mesh file |
| `mesh_statistics` | Cell volumes, quality metrics |
| `screenshot_mesh` | Publication-quality headless screenshot |
| `generate_internal_mesh_xml` | GEOS InternalMesh XML snippet |
| `define_geometry_box` | Single geometry Box XML snippet |
| `suggest_mesh_resolution` | Heuristic mesh resolution advisor |

### XML Assembly & Validation (13)

| Tool | Purpose |
|------|---------|
| `list_templates` | Available templates with descriptions |
| `generate_geometry_boxes` | All 7 standard BC boxes with correct cell-center sizing |
| `create_document` | New document (blank or from template) |
| `add_element` | Add element to a section |
| `update_element` | Modify element attributes |
| `remove_element` | Remove element (reports dangling refs) |
| `add_child` | Add nested child element |
| `load_xml` | Load existing XML for editing |
| `save_xml` | Save + auto-validate with xmllint |
| `preview_xml` | Write preview to file for readable display |
| `validate_xml` | xmllint schema validation |
| `validate_cross_references` | Check all internal name references resolve |
| `diff_xml` | Structured diff between two XML files |

### Post-Processing & Verification (8)

| Tool | Purpose |
|------|---------|
| `read_vtk_output` | Inspect arrays, scalar ranges |
| `extract_field` | Min/max/mean/std statistics |
| `screenshot_field` | Publication-quality field visualization |
| `compare_timesteps` | Field evolution over time |
| `compute_darcy_velocity` | Derive v = -(k/μ)∇p from pressure field |
| `compute_material_balance` | Reserves estimation from production data |
| `compute_well_performance` | Quick well rate sanity check |
| `sanity_check` | Physics heuristics + structural checks |

## GEOS Constitutive Assembly Pattern

Every GEOS simulation requires a specific constitutive assembly in the `<Constitutive>` section:

```xml
<Constitutive>
  <!-- Fluid model (referenced in materialList) -->
  <CompressibleSinglePhaseFluid name="water" ... />

  <!-- Coupled solid (referenced in materialList) -->
  <CompressibleSolidConstantPermeability name="rock"
    solidModelName="nullSolid"
    porosityModelName="rockPorosity"
    permeabilityModelName="rockPerm"/>

  <!-- Sub-models (NOT in materialList — referenced by coupled solid) -->
  <NullModel name="nullSolid"/>
  <PressurePorosity name="rockPorosity" ... />
  <ConstantPermeability name="rockPerm" ... />
</Constitutive>

<ElementRegions>
  <!-- materialList references ONLY: fluid + coupledSolid [+ relperm] [+ cappres] -->
  <CellElementRegion name="region"
    cellBlocks="{ block }"
    materialList="{ water, rock }"/>
</ElementRegions>
```

The agent handles this assembly automatically via the `recommend_fluid_model` tool and validated templates.

## Supported Physics (v0.1)

### In Scope

| Category | Models |
|----------|--------|
| **Single-phase flow** | SinglePhaseFVM, SinglePhaseHybridFVM |
| **Compositional multiphase** | CompositionalMultiphaseFVM, CompositionalMultiphaseHybridFVM |
| **CO2-brine** | CO2BrinePhillipsFluid |
| **Dead oil** | DeadOilFluid (knowledge base ready) |
| **Thermal coupling** | isThermal + ThermalCompressibleSinglePhaseFluid |
| **Relative permeability** | BrooksCoreyRelativePermeability, TableRelativePermeability (from user data) |
| **Non-solver sections** | Mesh, Events, Outputs, FieldSpecifications, Geometry, Functions |

### Deferred

- Poromechanics / geomechanics solvers
- Acoustic / seismic / earthquake solvers
- Table-based capillary pressure (TableCapillaryPressure, JFunctionCapillaryPressure)
- Soreide-Whitson EOS (CompositionalTwoPhaseFluidPhillipsBrine)
- Unstructured mesh generation (GMSH)
- CO2BrineEzrokhiFluid

## HPC / Airgapped Installation

```bash
# On workstation (with internet):
cd ~/codes/agents4geosx
uv export --frozen --all-extras > requirements.txt

# Transfer the repo + requirements.txt to the cluster

# On cluster (no internet):
uv sync --offline --all-extras
# Same MCP + skill registration as above
```

## Development

### Run tests

```bash
cd ~/codes/agents4geosx
uv run pytest tests/ -v
```

### Project structure

```
agents4geosx/
├── src/agents4geosx/
│   ├── server.py              # FastMCP server entry point
│   ├── config.py              # Schema path resolution
│   ├── tools/                 # 5 tool modules (46 tools total)
│   │   ├── schema_tools.py    # Schema introspection (7)
│   │   ├── fluid_tools.py     # Fluid PVT + constitutive (10)
│   │   ├── mesh_tools.py      # Mesh creation + viz (8)
│   │   ├── xml_tools.py       # XML assembly + validation (13)
│   │   └── postproc_tools.py  # Post-processing (8)
│   ├── state/
│   │   └── documents.py       # In-memory DocumentStore (doc_id → DocumentState)
│   └── knowledge/             # Domain knowledge from GEOS inputFiles audit
│       ├── field_names.py     # Solver → valid BC/IC field names
│       ├── cross_refs.py      # Attribute cross-reference graph
│       ├── sanity_rules.py    # Physics heuristic checks
│       └── fluid_models.py    # NL → constitutive assembly mapping
├── skills/                    # Claude Code slash commands (10 .md files)
├── hooks/                     # Auto-validation + auto-screenshot hooks
├── tests/                     # 42 tests (schema, fluid, mesh, XML, postproc, integration)
└── examples/                  # Example conversation transcripts
```

## License

TBD

## Acknowledgements

- [GEOS](https://github.com/GEOS-DEV/GEOS) — Lawrence Livermore National Laboratory, Stanford University, TotalEnergies
- [pyResToolbox](https://github.com/mwburgoyne/pyResToolbox) — Mark W. Burgoyne (original); SI unit refactoring by Adriano Cortes
- [PyVista](https://github.com/pyvista/pyvista) — PyVista developers
- [FastMCP](https://github.com/prefecthq/fastmcp) — Prefect
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic
