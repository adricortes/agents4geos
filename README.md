# Agents4GEOSX

A team of specialized AI agents for creating and editing [GEOS](https://github.com/GEOS-DEV/GEOS) simulation input files, built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) MCP server with slash commands and hooks.

GEOS simulations require complex XML input files — often 200-500 lines of cross-referenced parameters across solvers, constitutive models, mesh, boundary conditions, and outputs. Agents4GEOSX lets you describe your simulation in plain English and a team of agents — each specialized in schema, fluids, meshing, validation, or post-processing — collaborates to produce validated XML, backed by real physics computations and knowledge learned from 200+ official GEOS examples.

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
| `/geos:curate-errors` | Curate runtime error logs for pattern learning |

## Architecture

Agents4GEOSX is a layered system — see [AGENTS.md](AGENTS.md) for the full taxonomy, agent registry, and coordination patterns.

```
User ──── /geos "create a CO2 injection simulation..."
             │
Agents ─── 11 slash-command agents (Tier 1-3 model routing)
             │  orchestrator + schema, edit, validate, fluids,
             │  mesh, relperm, inspect, run, postprocess, curate-errors
             │
Tools ──── 52 MCP tools in 6 groups (FastMCP server)
             │
Knowledge ─ Domain patterns from 200+ GEOS input files
```

### Tool Groups

| Group | Tools | Powered by | Purpose |
|-------|-------|------------|---------|
| **Schema & Introspection** | 7 | geos-tui schema parser | Query elements, attributes, types, cross-references |
| **Fluid & Constitutive** | 10 | pyResToolbox (SI) | Gas/oil/brine PVT, relperm, cap pressure, well IPR |
| **Mesh** | 8 | PyVista | Create/load meshes, statistics, screenshots, XML generation |
| **XML Assembly & Validation** | 14 | geos-tui + xmllint | Create/load/edit/save documents, validate, templates |
| **Post-Processing** | 9 | PyVista + pyResToolbox | VTK analysis, field viz, Darcy velocity, material balance |
| **Preprocessing** | 4 | Knowledge modules | Unit conversion, parameter expansion, include resolution, XML formatting |

For the full tool inventory and agent-tool mappings, see [AGENTS.md §4](AGENTS.md#4-tool-inventory).

## Supported Physics (v0.1)

| Category | Models |
|----------|--------|
| **Single-phase flow** | SinglePhaseFVM, SinglePhaseHybridFVM |
| **Compositional multiphase** | CompositionalMultiphaseFVM, CompositionalMultiphaseHybridFVM |
| **CO2-brine** | CO2BrinePhillipsFluid |
| **Dead oil** | DeadOilFluid |
| **Thermal coupling** | isThermal + ThermalCompressibleSinglePhaseFluid |
| **Relative permeability** | BrooksCoreyRelativePermeability, TableRelativePermeability |
| **Non-solver sections** | Mesh, Events, Outputs, FieldSpecifications, Geometry, Functions |

Poromechanics, geomechanics, acoustic/seismic, and unstructured mesh generation are deferred — see [CLAUDE.md](../../geos-tui/CLAUDE.md) for the full scope definition.

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
├── AGENTS.md                  # Agent architecture (taxonomy, tiers, registry, patterns)
├── CLAUDE.md                  # Quick reference for Claude Code
├── src/agents4geosx/
│   ├── server.py              # FastMCP server entry point
│   ├── config.py              # Schema path resolution
│   ├── tools/                 # 6 tool modules (52 tools total)
│   │   ├── schema_tools.py    # Schema introspection (7)
│   │   ├── fluid_tools.py     # Fluid PVT + constitutive (10)
│   │   ├── mesh_tools.py      # Mesh creation + viz (8)
│   │   ├── xml_tools.py       # XML assembly + validation (14)
│   │   ├── postproc_tools.py  # Post-processing (9)
│   │   └── preproc_tools.py   # Preprocessing (4)
│   ├── state/
│   │   └── documents.py       # In-memory DocumentStore (doc_id → DocumentState)
│   └── knowledge/             # Domain knowledge from GEOS inputFiles audit
│       ├── field_names.py     # Solver → valid BC/IC field names
│       ├── cross_refs.py      # Attribute cross-reference graph
│       ├── sanity_rules.py    # Physics heuristic checks
│       └── fluid_models.py    # NL → constitutive assembly mapping
├── skills/                    # Claude Code slash commands (11 .md files)
├── hooks/                     # Auto-validation + auto-screenshot hooks
├── tests/                     # 49 tests (schema, fluid, mesh, XML, postproc, integration)
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
