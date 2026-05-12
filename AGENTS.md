# AGENTS.md — Agents4GEOS

This document formalizes the Agents4GEOS architecture. It serves both as
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

---

## 4. Tool Inventory

51 MCP tools + `health_check`, grouped by domain.

### Schema & Introspection (7 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `list_sections` | Top-level XML sections | schema, geos |
| `list_elements` | Elements in a section (v1 filtered) | schema, geos |
| `describe_element` | Full element detail (attrs, children, description) | schema, inspect, geos |
| `list_attributes` | Attributes by group (essential/physics/advanced) | schema, geos |
| `get_type_info` | Type constraints, patterns, enums | schema |
| `lookup_field_names` | Valid BC/IC fields per solver | schema, geos |
| `get_cross_references` | Attribute → section mapping | schema, geos |

### Fluid & Constitutive (10 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `compute_gas_properties` | Z-factor, density, viscosity, Bg, Cg (SI) | fluids |
| `compute_oil_properties` | Pb, Rs, Bo, density, viscosity (SI) | fluids |
| `compute_brine_properties` | Brine density, viscosity, Bw (SI) | fluids |
| `generate_pvt_table` | PVT table over pressure range | fluids |
| `generate_rel_perm` | Brooks-Corey/VG/LET relperm curves | relperm |
| `fit_rel_perm` | Fit relperm model to measured data | relperm |
| `generate_cap_pressure` | Brooks-Corey/VG capillary pressure curves | relperm |
| `compute_well_ipr` | Radial flow well IPR | fluids |
| `create_table_rel_perm_xml` | TableRelativePermeability + TableFunction XML | relperm |
| `recommend_fluid_model` | NL → solver + full constitutive assembly | fluids, geos |

### Mesh (8 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `create_structured_mesh` | Uniform grid → VTK | mesh |
| `create_rectilinear_mesh` | Variable-spacing grid → VTK | mesh |
| `load_mesh` | Inspect existing mesh file | mesh |
| `mesh_statistics` | Cell volumes, quality metrics | mesh |
| `screenshot_mesh` | Headless mesh render | mesh |
| `generate_internal_mesh_xml` | GEOS InternalMesh XML snippet | mesh, geos |
| `define_geometry_box` | Single Box XML for BC regions | mesh, geos |
| `suggest_mesh_resolution` | Heuristic resolution advisor | mesh |

### XML Assembly & Validation (14 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `list_templates` | Available document templates | geos |
| `generate_geometry_boxes` | 7 standard BC boxes | geos |
| `create_document` | New doc (blank or template) | geos, edit |
| `add_element` | Add element to section | geos, edit |
| `update_element` | Modify element attributes | geos, edit |
| `remove_element` | Remove element + report dangling refs | edit |
| `add_child` | Add nested child element | geos, edit |
| `load_xml` | Load existing XML for editing | edit, validate, inspect |
| `save_xml` | Save + auto-validate with xmllint | edit, geos |
| `preview_xml` | Write preview to file | edit, inspect, geos |
| `validate_xml` | xmllint schema validation | validate |
| `validate_cross_references` | Check internal name refs resolve | validate, edit, geos |
| `diff_xml` | Structured diff between two files | edit |
| `log_runtime_error` | Log error to JSONL for learning | run, curate-errors |

### Post-Processing & Verification (7 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `read_vtk_output` | Inspect VTK arrays and ranges | postprocess, run |
| `extract_field` | Min/max/mean/std statistics | postprocess, run |
| `screenshot_field` | Publication-quality field visualization | postprocess, run |
| `compare_timesteps` | Field evolution over time | postprocess |
| `compute_darcy_velocity` | v = -(k/μ)∇p from pressure field | postprocess |
| `compute_material_balance` | Original-in-place estimate | postprocess |
| `compute_well_performance` | Well rate sanity check | postprocess |

### Utility (2 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `health_check` | Server status | any |
| `sanity_check` | Physics heuristics + structural checks | validate, edit, geos |

### Preprocessing (4 tools)

| Tool | Purpose | Used by |
|------|---------|---------|
| `convert_units` | Parse GEOS bracket notation, convert to SI | fluids, geos, edit |
| `expand_parameters` | Resolve $Name$ patterns from Parameters section | edit, inspect, geos |
| `resolve_includes` | Merge `<Included>` file blocks into document | edit, inspect, validate |
| `format_xml` | Format XML to canonical geos-xml-tools style | edit, geos |

---

## 5. Knowledge Modules

Domain knowledge sourced primarily from an audit of 200+ official GEOS input files,
supplemented by runtime error lessons.

| Module | File | What it encodes | Provenance | Consumed by tools |
|--------|------|----------------|------------|-------------------|
| **Field names** | `src/agents4geos/knowledge/field_names.py` | Solver type → valid BC/IC field names | GEOS inputFiles audit | `lookup_field_names`, `sanity_check` |
| **Fluid models** | `src/agents4geos/knowledge/fluid_models.py` | NL keywords → solver + constitutive assembly (6 scenarios) | GEOS inputFiles audit + curated physics defaults | `recommend_fluid_model` |
| **Cross-references** | `src/agents4geos/knowledge/cross_refs.py` | Attribute → target section mapping | XSD schema structure | `get_cross_references`, `validate_cross_references` |
| **Sanity rules** | `src/agents4geos/knowledge/sanity_rules.py` | Physics heuristics + structural checks | GEOS inputFiles audit + runtime errors | `sanity_check` |
| **Lessons learned** | `knowledge/lessons_learned.md` | Runtime error patterns + fixes (prose) | Curated from GEOS runs | `geos:run`, `geos:curate-errors` (read by agent, not tool) |

**Key principle:** Knowledge modules are the single source of truth for domain patterns.
Tools read from them — they never hardcode domain logic. When a new pattern is discovered
(e.g., via runtime error logging), it gets added to the appropriate knowledge module, not
to a tool.

---

## 6. Coordination Patterns

### Pipeline

Agent A produces structured output → Agent B validates/transforms it → Agent C acts on it.
Each stage has a clear input/output contract. If a stage fails, the pipeline halts — it
does not silently pass garbage downstream.

*Current example:* `geos:fluids` (recommend model) → `geos` (assemble XML) → `geos:validate` (check result)

*Anticipated example:* PDF reader (extract data) → Reviewer (validate coherence) → `geos` (build simulation)

### Fan-out

The orchestrator dispatches multiple independent agents in parallel, then merges results.
Useful when subtasks have no shared state.

*Current example:* `geos` dispatching `geos:mesh` and `geos:fluids` concurrently — mesh creation and fluid model selection are independent.

### Feedback loop

Agent A produces output → Agent B reviews it → if issues found, Agent A is re-invoked
with the review feedback. Bounded by a max-iteration count to prevent infinite cycles.

*Anticipated example:* PDF reader extracts a table → Reviewer flags inconsistencies → PDF reader re-extracts with corrective instructions → Reviewer approves.

### Cross-cutting principles

- Every agent-to-agent handoff must pass **structured data** (dicts, tables), never free-form prose
- The orchestrator (`geos`) is the only agent that talks to the user — sub-agents report back to the orchestrator
- Quality gates (reviewer agents) are recommended for any pipeline that ingests external data (PDFs, user-provided tables, third-party files)

---

## 7. Extension Guide

### Conventions

- Each agent gets a skill file in `skills/` named `geos:<domain>.md`
- Each agent gets an entry in the Agent Registry (Section 3)
- New MCP tools go in `tools/<group>_tools.py` (or a new file if no group fits)
- New domain knowledge goes in `knowledge/<module>.py` with provenance documented
- New coordination patterns get documented in Section 6

### Template for new agent entry

    **`geos:<name>`** — Tier <1|2|3>
    - *Description:* <one-line purpose>
    - *Tools:* <list of MCP tools this agent may call>
    - *Knowledge:* <knowledge modules it depends on, or "None">
    - *Inputs:* <what it receives>
    - *Outputs:* <what it produces>
    - *Coordination:* <pattern it participates in, e.g., "pipeline stage 2 after geos:read-pdf">

### Checklist for adding a new agent

1. Write the skill file (`skills/geos:<name>.md`)
2. Add tools if needed (with tests)
3. Add knowledge modules if needed (with provenance documented)
4. Add the agent entry to this file's Agent Registry (Section 3)
5. Update the Tool Inventory (Section 4) if new tools were added
6. If the agent introduces a new coordination pattern, document it in Section 6
