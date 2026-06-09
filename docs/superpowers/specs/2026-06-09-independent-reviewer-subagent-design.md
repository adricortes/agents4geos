# Independent Reviewer Subagent + Bounded Fix Loop — Design

**Date:** 2026-06-09
**Status:** Approved (pending spec review)
**Beads:** `agents4geos-w9k` (child of epic `agents4geos-gy9`, "Push agent capabilities")

## Problem

Every agents4geos operation runs in the **main conversation on one model**. The
11 entries in `skills/` are prompt overlays, not subagents — none invokes the
Agent/Task tool, none declares a `model:`. Consequently:

- The AGENTS.md Tier1/2/3 → Haiku/Sonnet/Opus routing is aspirational; nothing
  wires it.
- Validation (`geos:validate`, `sanity_check`, `validate_cross_references`) runs
  in the **same context** that built the deck, so it shares the builder's blind
  spots. It cannot catch semantic intent-mismatch ("user asked for 1 year, deck
  runs 1 month"; "injector on the wrong face").

## Goal

Introduce the project's first real subagent: a **fresh-context independent
reviewer** dispatched by the orchestrator after a deck is built, driving a
**bounded fix loop**. This is the highest-priority driver the user named
(correctness via review) and establishes the reusable dispatch+review+loop
pattern that later capability (#2 autonomy) and knowledge (#3 Dolt) work build on.

## Load-bearing assumption (verify FIRST)

A subagent dispatched via the Agent tool **inherits access to the `agents4geos`
MCP server** — so the reviewer can call `validate_xml` / `load_xml` /
`validate_cross_references` / `sanity_check` and read the shared in-memory
`DocumentStore` by `doc_id`. ~90% confident from Claude Code semantics. **If this
is false, the data flow changes** (reviewer would have to read a written preview
file only, and re-parse rather than share state). Verification is implementation
step 1, before anything else is built.

## Architecture & data flow

```
User request ──► geos orchestrator (Opus)
                    │  builds deck via MCP tools (existing flow)
                    │  preview_xml → file ; doc_id retained in DocumentStore
                    ▼
              ┌─ Agent tool dispatch ─────────────────────┐
              │  geos-reviewer subagent (FRESH context)    │
              │  inputs: artifact (preview path + doc_id)  │
              │          + ORIGINAL user request verbatim  │
              │  1. validate_xml / x-refs / sanity_check   │  shares same
              │  2. judges intent-match & physics realism  │  MCP DocumentStore
              │  returns: structured findings (JSON)       │
              └────────────────────────────────────────────┘
                    │
              blocking findings? ──no──► present deck to user ✓
                    │ yes
                    ▼
              orchestrator fixes via MCP edit tools
                    │  re-dispatch FRESH reviewer (loop, max 3)
                    └──► unresolved after 3: present deck + honest
                         "reviewer still flags these N issues" → user
```

## Components

### New: `.claude/agents/geos-reviewer.md`

First Claude Code subagent definition in the repo. Frontmatter:

- `name: geos-reviewer`
- `description:` independent fresh-context reviewer of a built GEOS deck
- `model: opus` — correctness is the #1 driver; a reviewer weaker than the Opus
  builder can miss subtle errors. This is the **first place tier→model routing
  actually executes.**
- `tools:` — agents4geos MCP read/validate tools (`validate_xml`, `load_xml`,
  `validate_cross_references`, `sanity_check`, `describe_element`,
  `lookup_field_names`, `get_cross_references`) + `Read`. No deck-editing tools
  (`update_element`/`add_element`/`save_xml`) — the reviewer judges, it does not
  mutate the deck. (`load_xml` adds a read-only doc to the store so the xref/
  sanity tools have a `doc_id` to operate on; that is reading, not editing.)

The reviewer is **deliberately blind** to how the deck was built. It receives
only (a) the artifact and (b) the user's original request, and:

1. Runs the deterministic checks (superset of `geos:validate`).
2. Adds the judgment the tools can't: **intent fidelity** (duration, injection/
   production rates, BC faces, domain dimensions, fluid type, output cadence)
   and physics plausibility beyond hardcoded ranges.
3. Returns **structured findings only** (never prose), per the AGENTS.md
   cross-cutting rule.

### Findings schema (also the Dolt seam)

```json
[{
  "severity": "error | warning | advisory",
  "category": "schema | xref | physics | intent",
  "location": "<section/element path>",
  "issue": "<what is wrong>",
  "suggested_fix": "<concrete remedy>",
  "intent_mismatch": true
}]
```

`severity` semantics match `geos:validate`: **error** = schema violation (GEOS
won't load), **warning** = broken xref / will crash at runtime, **advisory** =
sanity/physics concern. `error` and `warning` are **blocking** (drive the fix
loop); `advisory` is surfaced but non-blocking.

This schema is intentionally the shape a future Dolt `errors`/`lessons` table
would store, so #3 can add a "persist finding" sink **without changing this
contract**. Iteration 1 does not persist lessons.

### Modified: `skills/geos.md`

Add a final **"Independent Review Gate"** stage after deck assembly:

1. Ensure a preview exists (`preview_xml`) and the `doc_id` is known.
2. Dispatch `geos-reviewer` with the artifact references + the user's original
   request verbatim.
3. If findings contain any `error`/`warning`: fix them with MCP edit tools, then
   re-dispatch a **fresh** reviewer. Repeat, **max 3 iterations**.
4. On convergence (no blocking findings) or exhaustion: present the deck. If
   exhausted with residual blocking findings, tell the user **honestly** which
   issues remain unresolved — never silently present a deck the reviewer
   rejected.

### Modified: `AGENTS.md`

- §1 Taxonomy: note that agents may now be **real subagents** (Agent-tool
  dispatched, own context/model), not only prompt-overlay skills.
- §3 Registry: add `geos-reviewer` (Tier 3 — judgment/reasoning, model opus, the
  review/fix-loop participant).
- §6 Coordination: the feedback-loop pattern is now **realized** (was
  "anticipated") by the review gate.

### Relationship to `geos:validate`

`geos:validate` stays the **user-facing manual** slash command (run on demand
against any file). `geos-reviewer` is the **orchestrator-internal automatic**
gate with fresh context + intent awareness. They share the deterministic check
core; the reviewer is a superset. Minor prompt overlap is accepted for clarity
(no shared-include indirection in iteration 1).

## Model tiers

- Orchestrator: Opus (Tier 3, unchanged).
- Reviewer: **Opus** (the correctness gate).
- This makes tier→model routing real for the first time. Cheap-tier routing
  (Haiku for retrieval subagents) is a **later** layer that reuses this exact
  dispatch mechanism — out of scope here.

## Scope

**In:** one reviewer subagent; end-gate placement; bounded fix loop (max 3);
structured findings; honest non-convergence reporting; Opus reviewer; verify
MCP-access-from-subagent first.

**Out (future, explicitly deferred):** multi-stage review gates; cheap-tier cost
routing; auto-writing lessons to Dolt; parallel multi-lens review *teams* (driver
#1 capability/parallelism — layered on this foundation next).

## Testing

Agent behavior is not unit-testable like deterministic code. Approach:

1. **Reviewer eval harness** — fixtures under `tests/fixtures/review/`: decks
   with *seeded* defects (duration mismatch vs. a stated intent, injector on the
   wrong face, permeability out of range, broken cross-ref) paired with the
   intent string and the expected finding categories. A script dispatches the
   reviewer (or exercises its check logic) and scores **recall** of the seeded
   defects, plus a known-good deck that must yield **zero blocking** findings.
2. **Fix-loop logic** lives in the `geos.md` prompt and is verified via a couple
   of curated **end-to-end** scenarios (in the spirit of the `questions.md`
   prompts), not unit tests.

This is stated plainly: iteration 1 ships evals + curated scenarios, not
deterministic unit coverage of agent reasoning.

## Success criteria

- A subagent dispatched by the orchestrator can call agents4geos MCP tools and
  read the shared `DocumentStore` (assumption verified).
- On a deck with a seeded intent-mismatch the tools alone would pass, the
  reviewer flags it, and the orchestrator fixes it within 3 iterations.
- On a known-good deck the reviewer returns zero blocking findings and the deck
  is presented unchanged.
- Non-convergence after 3 iterations is reported to the user with the residual
  findings named.
- `AGENTS.md` registry and coordination sections reflect the realized pattern.
