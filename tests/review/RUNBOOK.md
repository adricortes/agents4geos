# geos-reviewer eval runbook

Agent-run eval — not a pytest. Measures whether the reviewer catches seeded
defects, especially the intent-mismatch the deterministic tools miss.

## Procedure
For each case in `tests/fixtures/review/manifest.json`:
1. Dispatch the `geos-reviewer` subagent (Agent tool) with:
   - the absolute path to `tests/fixtures/review/<case.name>.xml`,
   - the manifest `intent` string as the "user's original request",
   - the workspace absolute path.
2. Collect the returned JSON findings.
3. Score: did any finding have `category == case.expect_category` pointing at the
   seeded defect? (For `duration_mismatch`, a finding with
   `intent_mismatch: true` about run time.)

## Pass bar
- All `tool_catchable: true` cases: caught (these should be easy — the tools find
  them and the reviewer relays them).
- The `duration_mismatch` (intent) case: caught with `intent_mismatch: true`.
  THIS is the case that justifies the whole subagent — if it's missed, iterate on
  the reviewer instructions in `.claude/agents/geos-reviewer.md`.
- The known-good base deck (`good_single_phase.xml`) with the matching intent:
  returns `[]` (no blocking findings).

## Prerequisite: the reviewer needs the agents4geos MCP server
This eval can only run in a session where the `agents4geos` MCP server is
registered (README "Installation → Step 3"), AND where the `geos-reviewer`
subagent is loaded from `.claude/agents/`. The reviewer's tools are
`mcp__agents4geos__*`; without the server registered, it falls back to file-only
`Read` + cannot run `validate_cross_references`/`sanity_check`. Run this from a
real `/geos`-capable session, not a headless job that lacks the MCP server.

The diagnostic body shipped in Task 1 (now replaced) was the way to confirm MCP
access from a dispatched subagent. If you ever doubt the reviewer can reach the
tools, temporarily restore that diagnostic and dispatch it; expect
`{"mcp_accessible": true, ...}`.

## What the deterministic layer can and cannot catch (verified 2026-06-09)
`tests/review/test_fixtures.py` proves the contrast the LLM reviewer exists to
bridge. Confirmed against the current tools:
- `broken_materiallist_ref` — caught by `validate_cross_references`
  (`'nonexistentRock' not found in Constitutive`).
- `negative_pressure` — caught by `sanity_check` (`pressure_positive`).
- `duration_mismatch` — NOT caught: schema-valid, xref-clean, sanity-clean. Only
  the reviewer's intent-fidelity judgment can flag it. This is the load-bearing
  case for the whole subagent.

### Known deterministic-tool gaps (the reviewer must compensate)
While building the fixtures, three real limitations of the current sanity tools
surfaced. The LLM reviewer should catch these from the XML directly even though
the tools stay silent; they are also worth fixing in the tools (see beads):
1. `sanity_check` does `float(attr_value)`, so it skips any GEOS list literal
   (e.g. `permeabilityComponents="{ 1e-2, 1e-2, 1e-2 }"`). Out-of-range
   permeability is NOT tool-catchable — this is why the physics fixture is
   negative pressure, not permeability.
2. The sanity-rule matcher (`pattern in k.lower()`) does not lowercase the
   pattern, so mixed-case patterns (`referencePorosity`, `cflFactor`) never
   match any attribute — those rules are effectively dead.
3. `_collect_all_attrs` flattens attributes into a dict keyed by attribute name,
   so same-named attributes across elements (e.g. two `referencePressure`)
   collide; only the last-collected survives. The `negative_pressure` fixture
   sets BOTH occurrences so the surviving value is reliably negative.

## Record results
Append a dated results block to this file each run (date, per-case caught/missed),
so reviewer-instruction changes can be compared over time.

## Results log

### 2026-06-09 — baseline: PENDING (could not run in build session)
The implementing session was a headless background job WITHOUT the `agents4geos`
MCP server registered and WITHOUT the `geos-reviewer` subagent loaded into the
agent registry, so the live agent-run eval could not be executed. The
deterministic substrate it depends on IS verified (see
`tests/review/test_fixtures.py`, all green): the catchable defects are caught by
the tools and the intent defect passes through clean. The remaining unknown is
purely the LLM reviewer's intent-recall, which must be scored in a real
`/geos`-capable session.

**To close this baseline:** run the Procedure above in a session with the MCP
server registered, then replace this block with per-case caught/missed results.
Expected easy wins: `negative_pressure` (physics), `broken_materiallist_ref`
(xref). The bar to watch: `duration_mismatch` caught with `intent_mismatch: true`.
