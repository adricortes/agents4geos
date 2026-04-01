# README.md Refactor Design Specification

**Date:** 2026-04-01
**File:** `/home/adriano/codes/agents4geosx/README.md`
**Audience:** Users discovering the project on GitHub, collaborators, GEOS engineers

---

## Purpose

Refactor README.md to serve as a **user-facing quickstart with a lightweight
architecture overview**. Deep architecture details now live in AGENTS.md;
the README should answer "what is this, why should I care, and how do I use it?"
with a bird's-eye pointer to where to learn more.

---

## Design Decisions

1. **"Team of agents" framing** — the one-liner and value proposition emphasize
   the multi-agent nature of the system
2. **Usage before installation** — show value before asking for setup effort
3. **Compact tool summary** — 5-group table with counts, not 48 individual rows
   (full inventory in AGENTS.md §4)
4. **Slim physics scope** — table of what's supported, one-line deferred summary,
   no constitutive assembly XML example (the agent handles that)
5. **No duplication** — knowledge base, tool inventory, agent registry all link
   to AGENTS.md rather than repeating content

---

## New Section Order

### 1. Title + Value Proposition (rewritten)

```markdown
# Agents4GEOSX

A team of specialized AI agents for creating and editing GEOS simulation
input files, built as a Claude Code MCP server with slash commands and hooks.

GEOS simulations require complex XML input files — often 200-500 lines of
cross-referenced parameters across solvers, constitutive models, mesh,
boundary conditions, and outputs. Agents4GEOSX lets you describe your
simulation in plain English and a team of agents — each specialized in
schema, fluids, meshing, validation, or post-processing — collaborates
to produce validated XML, backed by real physics computations and knowledge
learned from 200+ official GEOS examples.
```

### 2. Usage Examples (existing, minor update)

Keep all 7 existing examples as-is. Update the slash commands summary table
to include `geos:curate-errors` (11 commands total).

### 3. Architecture Overview (rewritten)

Bird's-eye ASCII diagram showing 4 layers: User → Agents → Tools → Knowledge.
Compact 5-group tool table with counts and "powered by" column. Links to
AGENTS.md for full taxonomy, agent registry, and coordination patterns.

Updated tool counts:
- Schema: 7, Fluid: 10, Mesh: 8, XML: 14, Post-proc: 9
- Total: 48 (including health_check and sanity_check)

### 4. Supported Physics (trimmed)

In-scope table kept. Constitutive assembly XML example removed (internal
detail). Deferred list replaced with one-line summary linking to CLAUDE.md
scope definition.

### 5. Requirements + Installation (existing, minimal updates)

Kept as-is. No content changes needed — the steps are accurate and practical.

### 6. HPC / Airgapped Installation (existing)

Kept as-is.

### 7. Development (existing, updated counts)

- Test count: 49 (was 42)
- Tool count in project structure: 48 (was 46)
- Skill count: 11 (was 10)

### 8. License + Acknowledgements (existing)

Kept as-is. License remains TBD per user preference.

---

## Sections Removed

| Section | Reason | New location |
|---------|--------|--------------|
| MCP Tools Reference (48-row tables) | Duplicated by AGENTS.md §4 | AGENTS.md §4 |
| GEOS Constitutive Assembly Pattern | Internal detail the agent handles | Knowledge in agent, not user-facing |
| Knowledge Base | Duplicated by AGENTS.md §5 | AGENTS.md §5 |

---

## Success Criteria

- A GEOS engineer landing on the repo understands what this does and how to
  use it within 30 seconds of reading
- No content is duplicated between README.md and AGENTS.md
- All counts (tools, tests, skills) match current source
- Installation instructions remain complete and accurate
- README links to AGENTS.md for architecture depth
