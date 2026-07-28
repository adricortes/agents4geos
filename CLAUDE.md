# CLAUDE.md — Agents4GEOS

## Overview
MCP server providing 52 tools for natural-language GEOS XML input creation.
Built on an in-repo schema/XML engine (`src/agents4geos/geos/`, adopted from the
superseded geos-tui), pyResToolbox (fluid PVT), PyVista (mesh/VTK).

## Commands
- `uv sync --all-extras` — install all deps
- `uv run pytest tests/ -v` — run tests
- `uv run python -m agents4geos.server` — start MCP server

## Architecture
- `src/agents4geos/server.py` — FastMCP server, registers all tools
- `src/agents4geos/tools/` — 6 tool modules (schema, fluid, mesh, xml, postproc, preproc)
- `src/agents4geos/state/` — In-memory DocumentStore for stateful XML assembly
- `src/agents4geos/knowledge/` — Domain knowledge (field names, cross-refs, sanity rules)
- `skills/` — Claude Code slash command skills
- `hooks/` — Auto-validation and auto-screenshot hooks
- `AGENTS.md` — Agent architecture: taxonomy, tiers, registry, coordination patterns

## Schema/XML engine: `src/agents4geos/geos/`
The schema parser, XML reader/writer, templates, and validation live **in this
repo** at `src/agents4geos/geos/{schema,xml,domain}/` — imported as
`agents4geos.geos.*`. This engine was adopted from the now-superseded geos-tui
project (provenance in `src/agents4geos/geos/ORIGIN.md`); there is no external
geos-tui dependency. The repo is self-contained: `uv sync --all-extras` needs no
sibling repos. pyvista and pyResToolbox both come from PyPI. pyResToolbox is
**stock upstream** (`pyrestoolbox>=3.7.3`, `fluids` extra) consumed exclusively
through the SI boundary adapter `src/agents4geos/fluids/si_adapter.py` — all
tool-facing units are SI, standard conditions unified on ISO (15 °C, 101325 Pa).
Never import `pyrestoolbox` directly in tools; go through `si_adapter`. The old
SI fork (adricortes/pyResToolbox) is archived — do not pin or extend it.

## Schema source
The GEOS `schema.xsd` is a **GEOS build artifact**, not shipped by GEOS itself in
parsed form. A parsed schema is **bundled** at `src/agents4geos/.cache/schema.json`
(committed), so `get_schema()` works out of the box with no GEOS build. Set
`GEOS_SCHEMA=/path/to/GEOS/build/schema.xsd` to override the bundle with a fresh
parse. Only if the bundled cache is deleted *and* `GEOS_SCHEMA` is unset does
`get_schema()` raise a `FileNotFoundError` naming both fixes.




<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

## Local-only working material — NEVER commit or push
`.handoffs/`, `docs/superpowers/`, and `.superpowers/` are Adriano's private
working notes (agent handoffs, implementation plans, orchestration scratch).
They are gitignored and must never touch the remote: never `git add` them
(including `-f`), never copy their contents into tracked files, and never
include them in commits, PRs, or pushes.
