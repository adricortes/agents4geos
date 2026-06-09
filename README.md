# Agents4GEOS

A team of specialized AI agents for creating and editing [GEOS](https://github.com/GEOS-DEV/GEOS) simulation input files, built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) MCP server with slash commands and hooks.

GEOS simulations require complex XML input files — often 200-500 lines of cross-referenced parameters across solvers, constitutive models, mesh, boundary conditions, and outputs. Agents4GEOS lets you describe your simulation in plain English and a team of agents — each specialized in schema, fluids, meshing, validation, or post-processing — collaborates to produce validated XML, backed by real physics computations and knowledge learned from 200+ official GEOS examples.

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

Agents4GEOS is a layered system — see [AGENTS.md](AGENTS.md) for the full taxonomy, agent registry, and coordination patterns.

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
| **Schema & Introspection** | 7 | in-repo schema engine | Query elements, attributes, types, cross-references |
| **Fluid & Constitutive** | 10 | pyResToolbox (SI) | Gas/oil/brine PVT, relperm, cap pressure, well IPR |
| **Mesh** | 8 | PyVista | Create/load meshes, statistics, screenshots, XML generation |
| **XML Assembly & Validation** | 14 | in-repo XML engine + xmllint | Create/load/edit/save documents, validate, templates |
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

Poromechanics, geomechanics, acoustic/seismic, and unstructured mesh generation are deferred — see the Supported Physics list above for the v0.1 scope.

## Quick Start for Evaluators

```bash
git clone https://github.com/adricortes/agents4geos.git
cd agents4geos
uv sync --all-extras
```

That's it — no GEOS build and no sibling repositories are required. The parsed
GEOS schema is bundled (`src/agents4geos/.cache/schema.json`), and the
schema/XML engine lives in this repo (`src/agents4geos/geos/`). The `fluids`
extra pulls `pyResToolbox` (SI fork) from git automatically. Users who later
build GEOS can set `GEOS_SCHEMA` to override the bundled schema.

### Private dependency access (one-time)

The `fluids` extra fetches `pyResToolbox` from a **private** repo over `https`.
`uv sync` shells out to `git`, which needs an https credential — an SSH key
alone is not enough and you'll see `could not read Username for
'https://github.com'`. Configure auth **once** with either approach:

```bash
# Option A (recommended): GitHub CLI credential helper
gh auth login        # if not already logged in
gh auth setup-git    # makes git use your gh token for https

# Option B: rewrite adricortes https URLs to SSH (uses your SSH key)
git config --global url."git@github.com:adricortes/".insteadOf "https://github.com/adricortes/"
```

Then `uv sync --all-extras` succeeds.

Then register the MCP server — see [Installation → Step 3](#3-set-up-a-workspace).

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- `xmllint` (for schema validation)
- GEOS build with `schema.xsd` — **optional**; a parsed schema is bundled, set `GEOS_SCHEMA` only to override it

### Dependencies

| Dependency | Source | What it provides |
|------------|--------|------------------|
| `agents4geos.geos` (in-repo) | this repo, `src/agents4geos/geos/` | Schema parser, XML reader/writer, templates, validation (adopted from the superseded geos-tui) |
| [pyResToolbox](https://github.com/adricortes/pyResToolbox) (SI fork) | git pin (`fluids` extra) | Fluid PVT, relative permeability, well performance. Fork of [mwburgoyne/pyResToolbox](https://github.com/mwburgoyne/pyResToolbox) with comprehensive SI unit refactoring. |
| [PyVista](https://github.com/pyvista/pyvista) | PyPI `pyvista>=0.43` | Mesh creation, VTK I/O, headless visualization |

## Installation

### 1. Clone and install

```bash
cd ~/codes
git clone git@github.com:adricortes/agents4geos.git
cd agents4geos
uv sync --all-extras
```

### 2. Verify dependencies

```bash
uv run python -c "from agents4geos.config import get_schema; print('schema engine OK —', len(get_schema().elements), 'elements')"
uv run python -c "from pyrestoolbox import gas; print('pyResToolbox OK')"
uv run python -c "import pyvista as pv; print('PyVista OK')"
```

### 3. Set up a workspace

Create a separate directory for testing/using the agent:

```bash
mkdir -p ~/codes/agents4geos-workspace
cd ~/codes/agents4geos-workspace

# Deploy slash commands
mkdir -p .claude/commands
cp ~/codes/agents4geos/skills/*.md .claude/commands/

# Deploy subagents (e.g. geos-reviewer, dispatched automatically by /geos)
mkdir -p .claude/agents
cp ~/codes/agents4geos/.claude/agents/*.md .claude/agents/

# Register the MCP server (uses the bundled schema by default)
claude mcp add agents4geos -- \
  uv run --directory ~/codes/agents4geos \
  python -m agents4geos
```

To use your own GEOS build's schema instead of the bundled one, add
`env GEOS_SCHEMA=/path/to/GEOS/build/schema.xsd` before `uv run` above.

### 4. Auto-approve MCP tools (optional)

To avoid confirming every tool call during use:

```bash
cat > .claude/settings.local.json << 'EOF'
{
  "permissions": {
    "allow": [
      "mcp__agents4geos__*",
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
cd ~/codes/agents4geos-workspace
claude
```

## HPC / Airgapped Installation

```bash
# On workstation (with internet):
cd ~/codes/agents4geos
uv export --frozen --all-extras > requirements.txt

# Transfer the repo + requirements.txt to the cluster

# On cluster (no internet):
uv sync --offline --all-extras
# Same MCP + skill registration as above
```

## Development

### Run tests

```bash
cd ~/codes/agents4geos
uv run pytest tests/ -v
```

### Project structure

```
agents4geos/
├── AGENTS.md                  # Agent architecture (taxonomy, tiers, registry, patterns)
├── CLAUDE.md                  # Quick reference for Claude Code
├── src/agents4geos/
│   ├── server.py              # FastMCP server entry point
│   ├── config.py              # Schema path resolution
│   ├── geos/                  # In-repo schema/XML engine (adopted from geos-tui)
│   │   ├── schema/            # XSD parser, model, cache
│   │   ├── xml/               # XML reader/writer, document state
│   │   └── domain/            # Curation, descriptions, scope, templates
│   ├── .cache/schema.json     # Bundled parsed GEOS schema (no GEOS build needed)
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
├── tests/                     # 191 tests (schema, fluid, mesh, XML, postproc, integration)
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
