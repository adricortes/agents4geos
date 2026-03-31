# Agents4GEOSX

Natural language interface for creating and editing [GEOS](https://github.com/GEOS-DEV/GEOS) simulation input files, built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) MCP server with skills, slash commands, and hooks.

Instead of writing 200-500 lines of cross-referenced XML by hand, describe your simulation in plain English and let the agent assemble validated XML using structured tools backed by real physics computations.

## Architecture

```
User Layer        /geos create... | /geos:edit | /geos:validate | Natural language
                                    |
Agent Layer       Orchestrator skill + 9 slash commands + auto-validation hooks
                                    |  (MCP Protocol)
Tool Layer        FastMCP Server — 42 tools in 5 groups
                  Schema (7) | Fluids (9) | Mesh (8) | XML (11) | PostProc (7)
                                    |
Data Layer        schema.xsd | GEOS inputFiles/ | PVT tables | VTK outputs
```

### Tool Groups

| Group | Tools | Powered By | Purpose |
|-------|-------|------------|---------|
| **Schema & Introspection** | 7 | geos-tui schema parser | Query elements, attributes, types, cross-references |
| **Fluid & Constitutive** | 9 | pyResToolbox (SI units) | Gas/oil/brine PVT, rel perm, cap pressure, well IPR |
| **Mesh** | 8 | PyVista | Create/load meshes, statistics, headless screenshots, XML generation |
| **XML Assembly & Validation** | 11 | geos-tui XML R/W + xmllint | Create/load/edit/save documents, validate cross-refs |
| **Post-Processing** | 7 | PyVista + pyResToolbox | VTK output analysis, field screenshots, material balance |

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
| geos-tui | `../../geos-tui` (`~/geos-tui`) | Schema parser, XML reader/writer, templates, validation |
| pyResToolbox (SI fork) | `../pyResToolbox` (`~/codes/pyResToolbox`) | Fluid PVT, relative permeability, well performance. Fork of [mwburgoyne/pyResToolbox](https://github.com/mwburgoyne/pyResToolbox) with comprehensive SI unit refactoring. |
| [PyVista](https://github.com/pyvista/pyvista) | `../pyvista` | Mesh creation, VTK I/O, headless visualization |

## Installation

### 1. Clone and install

```bash
cd ~/codes
git clone <this-repo> agents4geosx
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
| **Dead oil** | DeadOilFluid (template ready) |
| **Thermal coupling** | isThermal + ThermalCompressibleSinglePhaseFluid |
| **Relative permeability** | BrooksCoreyRelativePermeability |
| **Non-solver sections** | Mesh, Events, Outputs, FieldSpecifications, Geometry, Functions |

### Deferred

- Poromechanics / geomechanics solvers
- Acoustic / seismic / earthquake solvers
- Table-based relative permeability and capillary pressure
- Soreide-Whitson EOS (CompositionalTwoPhaseFluidPhillipsBrine)
- Unstructured mesh generation (GMSH)

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
│   ├── tools/                 # 5 tool modules (42 tools total)
│   │   ├── schema_tools.py    # Schema introspection (7)
│   │   ├── fluid_tools.py     # Fluid PVT + constitutive (9)
│   │   ├── mesh_tools.py      # Mesh creation + viz (8)
│   │   ├── xml_tools.py       # XML assembly + validation (11)
│   │   └── postproc_tools.py  # Post-processing (7)
│   ├── state/
│   │   └── documents.py       # In-memory DocumentStore (doc_id → DocumentState)
│   └── knowledge/             # Domain knowledge from GEOS inputFiles audit
│       ├── field_names.py     # Solver → valid BC/IC field names
│       ├── cross_refs.py      # Attribute cross-reference graph
│       ├── sanity_rules.py    # Physics heuristic checks
│       └── fluid_models.py    # NL → constitutive assembly mapping
├── skills/                    # Claude Code slash commands (9 .md files)
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
