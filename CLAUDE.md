# CLAUDE.md — Agents4GEOS

## Overview
MCP server providing 52 tools for natural-language GEOS XML input creation.
Built on geos-tui (schema/xml), pyResToolbox (fluid PVT), PyVista (mesh/VTK).

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

## Key dependency: geos-tui
Schema path default: resolved via GEOS_SCHEMA env var or ../../geos-tui/geos/build/schema.xsd




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
