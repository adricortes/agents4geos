# AGENTS.md Design Specification

**Date:** 2026-04-01
**Location:** `/home/adriano/codes/agents4geosx/AGENTS.md`
**Audience:** Claude Code (as operational instructions) and human developers (as architecture docs)

---

## Purpose

Create an `AGENTS.md` file that formalizes the Agents4GEOSX architecture: what each
entity is, how they coordinate, model routing by capability tier, and how to extend
the system with new agents.

This document is **descriptive** — it captures the existing system as-is. New agents
(e.g., PDF reader, data reviewer) are anticipated but not specified here; the extension
guide provides the pattern for adding them when the time comes.

---

## Document Structure

The `AGENTS.md` has 7 sections, ordered from concepts to specifics:

### Section 1: Taxonomy

Defines the five entity types in Agents4GEOSX:

| Term | Definition |
|------|-----------|
| **Agent** | A skill file that gives Claude a specific role, workflow, and decision-making authority. Has: name, capability tier, tool set, knowledge dependencies, defined inputs/outputs. Claude is the runtime; the agent is the configuration. |
| **Tool** | A stateless MCP function. Takes inputs, returns outputs. No memory, no decisions. Tools don't know about each other. |
| **Knowledge module** | A static Python data structure encoding domain patterns (field names, constitutive assemblies, sanity rules, cross-references). Sourced from the GEOS inputFiles audit + runtime error lessons. Tools read from knowledge modules; agents don't access them directly. |
| **State** | The DocumentStore — an in-memory key-value store (doc_id -> XML document). Shared across tool calls within a session. No persistence across sessions. |
| **Hook** | A shell script triggered automatically by Claude Code after tool use (e.g., auto-validate XML). Not an agent — no decisions, just reactions. |

**Key distinction:** Tools do work, knowledge encodes domain expertise, agents make
decisions about what work to do and in what order.

### Section 2: Capability Tiers & Model Routing

Three tiers based on cognitive complexity:

| Tier | Complexity | Model | Examples |
|------|-----------|-------|---------|
| **Tier 1: Retrieval** | Lookup, extraction, formatting | Haiku | Schema queries, field listing, PDF text extraction |
| **Tier 2: Synthesis** | Combining data, assembly, validation | Sonnet | XML assembly, cross-reference validation, fluid computation |
| **Tier 3: Planning** | Multi-step reasoning, user dialogue, creative decisions | Opus | Main orchestrator, simulation design, debugging runtime errors |

Routing principles:
- Use the cheapest model that can reliably handle the task
- When in doubt, tier up — a wrong answer from a cheap model costs more than the savings
- Tiers are recommendations, not hard constraints — the user can override
- As models improve, agents may move down a tier without changing their definition

### Section 3: Agent Registry

Each agent entry uses this format:

```
**`geos:<name>`** — Tier <N>
- *Description:* <one line>
- *Tools:* <list>
- *Knowledge:* <modules or "None">
- *Inputs:* <what it receives>
- *Outputs:* <what it produces>
```

The 11 current agents and their tier assignments:

| Agent | Tier | Description |
|-------|------|-------------|
| `geos` | 3 | Main orchestrator — create, edit, query simulations |
| `geos:schema` | 1 | Query GEOS XSD schema |
| `geos:edit` | 2 | Load, modify, validate, save existing XML |
| `geos:validate` | 2 | Schema + cross-ref + physics sanity checks |
| `geos:fluids` | 2 | Fluid PVT properties, model recommendation |
| `geos:mesh` | 2 | Mesh creation and visualization |
| `geos:relperm` | 2 | Relative permeability curves |
| `geos:inspect` | 1 | Describe XML file contents |
| `geos:run` | 3 | Run GEOS, analyze output, log errors |
| `geos:postprocess` | 2 | VTK analysis, material balance, well performance |
| `geos:curate-errors` | 1 | Curate runtime error logs |

Full details (tools, knowledge deps, inputs, outputs) for each agent are included
in the agent registry section of the document.

### Section 4: Tool Inventory

A table of all 46 MCP tools + `health_check`, grouped by domain (Schema, Fluid, Mesh,
XML, Post-proc, Utility). Each row has: tool name, purpose, and which agents use it.

This serves as a cross-reference — given a tool, you can see which agents depend on it;
given an agent, you can see what tools it has access to.

### Section 5: Knowledge Modules

Table of the 4 Python knowledge modules + the `lessons_learned.md` prose document:

| Module | What it encodes | Provenance | Consumed by |
|--------|----------------|------------|-------------|
| `field_names.py` | Solver -> valid BC/IC fields | GEOS inputFiles audit | `lookup_field_names`, `sanity_check` |
| `fluid_models.py` | NL keywords -> constitutive assembly | GEOS inputFiles audit | `recommend_fluid_model` |
| `cross_refs.py` | Attribute -> target section | XSD schema | `get_cross_references`, `validate_cross_references` |
| `sanity_rules.py` | Physics heuristics + structural checks | GEOS inputFiles audit + runtime errors | `sanity_check` |
| `lessons_learned.md` | Runtime error patterns + fixes | Curated from GEOS runs | `geos:run`, `geos:curate-errors` |

Key principle: Knowledge modules are the single source of truth for domain patterns.
Tools read from them — they never hardcode domain logic. New patterns go into
knowledge modules, not tools.

### Section 6: Coordination Patterns

Three named patterns:

**Pipeline:** Agent A -> Agent B -> Agent C. Each stage has a clear input/output
contract. If a stage fails, the pipeline halts.
- *Current:* `geos:fluids` -> `geos` -> `geos:validate`
- *Anticipated:* PDF reader -> Reviewer -> `geos`

**Fan-out:** Orchestrator dispatches independent agents in parallel, merges results.
- *Current:* `geos` dispatching `geos:mesh` + `geos:fluids` concurrently

**Feedback loop:** Agent A -> Agent B reviews -> if issues, re-invoke A with feedback.
Bounded by max iterations.
- *Anticipated:* PDF reader -> Reviewer -> (re-extract if needed) -> Reviewer approves

Cross-cutting principles:
- Agent-to-agent handoffs pass structured data (dicts, tables), never free-form prose
- The orchestrator (`geos`) is the only agent that talks to the user
- Quality gates (reviewer agents) are recommended for any pipeline ingesting external data

### Section 7: Extension Guide

**Conventions:**
- Each agent gets a skill file: `skills/geos:<domain>.md`
- Each agent gets an entry in the Agent Registry
- New tools go in `tools/<group>_tools.py` (or new file if no group fits)
- New domain knowledge goes in `knowledge/<module>.py` with provenance documented
- New coordination patterns get documented in Section 6

**Template:** A copy-paste template for agent registry entries.

**Checklist for adding a new agent:**
1. Write the skill file
2. Add tools if needed (with tests)
3. Add knowledge modules if needed (with provenance)
4. Add agent entry to AGENTS.md registry
5. Update tool inventory if new tools added
6. Document new coordination patterns if introduced

---

## Non-goals

- This document does NOT spec new agents (PDF reader, reviewer, etc.) — those will be
  designed in their own brainstorming sessions when the time comes
- This document does NOT prescribe specific model versions — tiers map to capability
  classes (Haiku/Sonnet/Opus), not version numbers
- This document does NOT duplicate tool signatures — those live in the source code

---

## Success Criteria

- Claude Code can read `AGENTS.md` and understand: what each entity is, which model
  to use for a given task, what tools an agent has access to, and how to add a new agent
- A human developer can read it and understand the full architecture without reading
  every skill file and tool module
- The extension guide is clear enough that a new agent can be added by following the
  template and checklist alone
