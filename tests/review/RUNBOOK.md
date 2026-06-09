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

### 2026-06-09 — Task 1 hard gate: PASSED (live); intent-recall: PENDING
Run from `/home/adriano/codes/agents4geos-workspace` with the `agents4geos` MCP
server registered (GEOS_SCHEMA → the compiled `/home/adriano/geos-stack/GEOS/build/schema.xsd`,
reached via the workspace `geos` symlink), against
`fixtures/review/broken_materiallist_ref.xml`.

**MCP-access gate (Task 1) — PASSED.** A throwaway `geos-mcp-probe` subagent
(haiku) dispatched via the Agent tool successfully called all three MCP tools
from its own context:
- `describe_element("SinglePhaseFVM")` → full attribute set returned
  (`described_ok: true`).
- `load_xml(...)` → `doc_id: doc_c4d2999a`, 21 elements, `unknown_elements: 0`
  (deck parses cleanly against the live compiled schema).
- `validate_cross_references(doc_id)` → flagged
  `'nonexistentRock' not found in Constitutive`.
The doc loaded in one tool call persisted for the next call within the subagent's
MCP session — confirming the shared module-level `DocumentStore` is reachable
across a dispatched subagent's tool calls. **The design's data flow is valid; the
file-only fallback is NOT needed.**

**Intent-recall (Task 5 / Task 8) — `duration_mismatch`: CAUGHT.** The real
`geos-reviewer` dispatched on `duration_mismatch.xml` with the manifest intent
returned an `intent` finding, `intent_mismatch: true`, identifying
`maxTime=2.6e6` (~30 days) vs. the requested 1 year and suggesting `3.15e7` —
the exact case the deterministic layer provably misses. It also independently
flagged geometry (slab vs. 100 m cube) and output-cadence (`timeFrequency=1e3`
vs. monthly) mismatches, auditing the whole deck rather than anchoring on the
filename. **Reviewer recall verified for the headline intent case.**

**Fixture refinement (post-Test-B).** Those bonus findings exposed that the
original base deck (the raw `single_phase_flow` template: 10x1x1 m slab,
`maxTime=1e4`, output every `1e3` s) was NOT faithful to the manifest intent, so
`duration_mismatch` was not a *singular* deviation. The fixtures were regenerated
from a base made faithful to the intent (100 m cube via xyz `{0,100}` + 10^3
cells, `maxTime=3.15e7`, output `timeFrequency=2.628e6`). Each defect deck is now
a single attributable deviation from that base; `good_single_phase.xml` is
xref-clean and sanity-clean and should now elicit no blocking findings.

**Intent-recall — `negative_pressure`: CAUGHT.** The reviewer flagged the negative
`referencePressure` as `category: physics` in BOTH constitutive models it was
planted in (`CompressibleSinglePhaseFluid` + `PressurePorosity`), all
`intent_mismatch: false`, and correctly judged geometry/duration/output as
faithful (output cadence accepted as ~monthly, no false positive). Confirms the
four axes (schema/xref/physics/intent) are independent and the faithful base is a
clean control.

**Policy decision (2026-06-09): physics stays advisory; orchestrator asks.** The
reviewer grades physics as `advisory` (non-blocking) by design — physics is
heuristic and a "violation" may be a deliberate experiment/stress test. So Stage R
does NOT auto-fix physics and does NOT silently save: it surfaces each physics
advisory with a recommended fix and asks the user whether to fix or keep
(`skills/geos.md` Stage R step 5). Only schema `error` / xref `warning` (and
`intent` mismatches against the verbatim request) drive the auto-fix loop.

**Intent-recall — `broken_materiallist_ref`: CAUGHT.** The reviewer flagged the
dangling `materialList` ref (`category: xref`), identified the real model name
(`rock`), and proposed the concrete fix `{ fluid, rock }` — adding the
human-actionable "what should it have been?" layer on top of the tool's raw
"is there a dangling ref?". It also noted a subtle bonus (the 12th/year-end VTK
output may not land cleanly at `maxTime`).

**Severity-rubric refinement (2026-06-09).** Across the three reviews the labels
were inconsistent: a dangling xref (fatal at GEOS init) was graded `warning` while
a wrong-but-runnable duration was graded `error` — i.e. a deck that won't
initialize scored softer than one that runs but answers the wrong question. Gate
*behavior* was unaffected (error+warning both block; advisory asks), but the labels
were backwards for honest reporting / any future error-only policy. Fixed the
reviewer's severity rubric in `.claude/agents/geos-reviewer.md`: severity now grades
"how certain the deck is wrong + is it safe to auto-fix" (category carries the
kind). A dangling cross-ref or anything that won't load/init → `error`; likely
wrong at runtime → `warning`; heuristic/possibly-intentional (physics, minor
intent) → `advisory` (orchestrator asks). The `ReviewFinding` contract is
unchanged (still error/warning/advisory); only the reviewer's assignment guidance
changed.

**Negative control — `good_single_phase`: `[]` (run in a fresh, cleared session).**
The reviewer returned an empty findings array with no false positives, confirming
intent by unit conversion (`maxTime=3.15e7 s ≈ 1 yr`, `timeFrequency=2.628e6 s ≈
1 mo`, 100 m cube, water density/viscosity) rather than trusting attribute names.
Ran isolated (~5 tool calls, ~9k tokens) — verdict independent of how the deck was
authored. This is the no-cry-wolf control, and it was only meaningful once the base
deck was made intent-faithful.

**BASELINE COMPLETE (2026-06-09).** Live, MCP-registered session results:
| case | expected | result |
|------|----------|--------|
| MCP-access gate (probe subagent) | tools + shared store reachable | PASS |
| `duration_mismatch` | intent caught | PASS (`error`/intent, intent_mismatch) |
| `negative_pressure` | physics caught | PASS (`advisory`/physics, ×2 models) |
| `broken_materiallist_ref` | xref caught | PASS (xref + actionable fix; now `error`) |
| `good_single_phase` | `[]` | PASS (fresh session, no false positives) |

Decisions made during eval: physics stays `advisory` and the orchestrator asks the
user (may be a deliberate experiment); severity rubric grades by certainty-of-wrong
+ auto-fix safety (won't-init/contradicts-intent → `error`). Only remaining
verification: a real `/geos` build end-to-end through Stage R (Task 8) — exercised
naturally on the next deck creation.
