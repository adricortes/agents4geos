# CLAUDE.md — Agents4GEOSX

## Overview
MCP server providing 42 tools for natural-language GEOS XML input creation.
Built on geos-tui (schema/xml), pyResToolbox (fluid PVT), PyVista (mesh/VTK).

## Commands
- `uv sync --all-extras` — install all deps
- `uv run pytest tests/ -v` — run tests
- `uv run python -m agents4geosx.server` — start MCP server

## Architecture
- `src/agents4geosx/server.py` — FastMCP server, registers all tools
- `src/agents4geosx/tools/` — 5 tool modules (schema, fluid, mesh, xml, postproc)
- `src/agents4geosx/state/` — In-memory DocumentStore for stateful XML assembly
- `src/agents4geosx/knowledge/` — Domain knowledge (field names, cross-refs, sanity rules)
- `skills/` — Claude Code slash command skills
- `hooks/` — Auto-validation and auto-screenshot hooks

## Key dependency: geos-tui
Schema path default: resolved via GEOS_SCHEMA env var or ../../geos-tui/geos/build/schema.xsd
