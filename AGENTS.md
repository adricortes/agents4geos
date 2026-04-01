# AGENTS.md — Agents4GEOSX

This document formalizes the Agents4GEOSX architecture. It serves both as
operational instructions for Claude Code (defining agent boundaries, model
routing, and coordination rules) and as architecture documentation for
human developers.

**Spec:** `docs/superpowers/specs/2026-04-01-agents-md-design.md`

---

## 1. Taxonomy

Five entity types make up the system:

| Term | Definition |
|------|-----------|
| **Agent** | A skill file that gives Claude a specific role, workflow, and decision-making authority. Has: a name, a capability tier, a set of tools it may call, knowledge dependencies, and defined inputs/outputs. Claude is the runtime; the agent is the configuration that shapes its behavior. |
| **Tool** | A stateless MCP function (`@mcp.tool`). Takes inputs, returns outputs. No memory, no decisions. Tools don't know about each other. |
| **Knowledge module** | A static Python data structure encoding domain patterns (field names, constitutive assemblies, sanity rules, cross-references). Tools read from knowledge modules; agents don't access them directly. |
| **State** | The DocumentStore — an in-memory key-value store (`doc_id` → XML document). Shared across tool calls within a session. No persistence across sessions. |
| **Hook** | A shell script triggered automatically by Claude Code after tool use (e.g., auto-validate XML, auto-screenshot VTK). Not an agent — no decisions, just reactions. |

**Key distinction:** Tools do work, knowledge encodes domain expertise, agents make
decisions about what work to do and in what order.

---

## 2. Capability Tiers & Model Routing

Three tiers based on cognitive complexity:

| Tier | Complexity | Model | Examples |
|------|-----------|-------|---------|
| **Tier 1: Retrieval** | Lookup, extraction, formatting | Haiku | Schema queries, field listing, PDF text extraction, table formatting |
| **Tier 2: Synthesis** | Combining data, assembly, validation | Sonnet | XML document assembly, cross-reference validation, fluid property computation, data review |
| **Tier 3: Planning** | Multi-step reasoning, user dialogue, creative decisions | Opus | Main orchestrator, simulation design, debugging runtime errors |

**Routing principles:**
- Use the cheapest model that can reliably handle the task
- When in doubt, tier up — a wrong answer from a cheap model costs more than the savings
- Tiers are recommendations, not hard constraints — the user can override
- As models improve, agents may move down a tier without changing their definition
- Each agent declares its tier; the orchestrator (or user) decides model assignment at dispatch time

---

## 3. Agent Registry

**`geos`** (Main Orchestrator) — Tier 3
- *Description:* Entry point for creating, editing, and querying GEOS simulations
- *Tools:* All (can delegate to any tool)
- *Knowledge:* All modules (indirectly, via tools)
- *Inputs:* Natural language user request
- *Outputs:* Validated GEOS XML file, previews, explanations

**`geos:schema`** — Tier 1
- *Description:* Query GEOS XSD schema for elements, attributes, types, cross-references
- *Tools:* `list_sections`, `list_elements`, `describe_element`, `list_attributes`, `get_type_info`, `lookup_field_names`, `get_cross_references`
- *Knowledge:* `field_names`, `cross_refs`
- *Inputs:* Element name, type name, or natural language question about schema
- *Outputs:* Structured schema information

**`geos:edit`** — Tier 2
- *Description:* Load, modify, validate, and save existing XML files
- *Tools:* `load_xml`, `update_element`, `add_element`, `remove_element`, `add_child`, `validate_cross_references`, `sanity_check`, `preview_xml`, `save_xml`
- *Knowledge:* `cross_refs`, `sanity_rules`
- *Inputs:* XML file path + modification instructions
- *Outputs:* Modified and validated XML file

**`geos:validate`** — Tier 2
- *Description:* Schema check + cross-reference check + physics sanity check
- *Tools:* `validate_xml`, `load_xml`, `validate_cross_references`, `sanity_check`
- *Knowledge:* `sanity_rules`, `cross_refs`
- *Inputs:* XML file path
- *Outputs:* Grouped findings (errors, warnings, advisories)

**`geos:fluids`** — Tier 2
- *Description:* Compute fluid PVT properties, generate tables, recommend models
- *Tools:* `compute_gas_properties`, `compute_oil_properties`, `compute_brine_properties`, `generate_pvt_table`, `recommend_fluid_model`
- *Knowledge:* `fluid_models`
- *Inputs:* Fluid type + conditions, or natural language scenario description
- *Outputs:* Property values, PVT tables, or constitutive assembly recommendation

**`geos:mesh`** — Tier 2
- *Description:* Create and visualize meshes, define geometry boxes
- *Tools:* `create_structured_mesh`, `create_rectilinear_mesh`, `load_mesh`, `mesh_statistics`, `screenshot_mesh`, `generate_internal_mesh_xml`, `define_geometry_box`, `suggest_mesh_resolution`
- *Knowledge:* None
- *Inputs:* Domain dimensions, resolution, or mesh file path
- *Outputs:* VTK files, XML snippets, screenshots, statistics

**`geos:relperm`** — Tier 2
- *Description:* Generate relative permeability curves, fit models to data
- *Tools:* `generate_rel_perm`, `fit_rel_perm`, `generate_cap_pressure`, `create_table_rel_perm_xml`
- *Knowledge:* None
- *Inputs:* Model parameters or measured data
- *Outputs:* Relperm/capillary pressure tables, XML snippets

**`geos:inspect`** — Tier 1
- *Description:* Describe contents of an existing XML file
- *Tools:* `load_xml`, `preview_xml`, `describe_element`
- *Knowledge:* None
- *Inputs:* XML file path
- *Outputs:* Section-by-section summary of what the file contains

**`geos:run`** — Tier 3
- *Description:* Run GEOS simulation, analyze output, log runtime errors
- *Tools:* `log_runtime_error`, `read_vtk_output`, `extract_field`, `screenshot_field`, `compare_timesteps`
- *Knowledge:* `lessons_learned.md`
- *Inputs:* Simulation directory + GEOS binary path
- *Outputs:* Run status, error diagnosis, post-processing results

**`geos:postprocess`** — Tier 2
- *Description:* Analyze VTK output — fields, time evolution, material balance
- *Tools:* `read_vtk_output`, `extract_field`, `screenshot_field`, `compare_timesteps`, `compute_darcy_velocity`, `compute_material_balance`, `compute_well_performance`
- *Knowledge:* None
- *Inputs:* VTK file paths + field names
- *Outputs:* Statistics, screenshots, derived quantities

**`geos:curate-errors`** — Tier 1
- *Description:* Curate runtime error logs for pattern learning
- *Tools:* `log_runtime_error`
- *Knowledge:* `lessons_learned.md`
- *Inputs:* Error log directory
- *Outputs:* Curated JSONL + updated lessons learned
