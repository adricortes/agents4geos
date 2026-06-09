# Independent Reviewer Subagent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the project's first real subagent — a fresh-context `geos-reviewer` dispatched by the orchestrator after a deck is built, driving a bounded (max 3) fix loop that catches schema/xref/physics errors AND semantic intent-mismatch the inline tools can't.

**Architecture:** A Claude Code subagent definition (`.claude/agents/geos-reviewer.md`, `model: opus`) is dispatched via the Agent tool with the built artifact + the user's verbatim request. It runs the deterministic MCP validation tools (sharing the orchestrator's in-memory `DocumentStore`) and adds intent-fidelity judgment, returning structured findings. The orchestrator (`skills/geos.md`) fixes blocking findings and re-dispatches a fresh reviewer, up to 3 times, reporting honestly if it can't converge.

**Tech Stack:** Claude Code subagents + Agent tool, agents4geos MCP server (FastMCP), Python 3.11 + pytest for the deterministic findings contract and fixtures. Spec: `docs/superpowers/specs/2026-06-09-independent-reviewer-subagent-design.md`.

**Cold-start prerequisites (read before Task 1):**
- You are in `/home/adriano/codes/agents4geos` on a fresh branch (Task 1 creates it).
- The `agents4geos` MCP server must be registered in this session (see README "Installation → Step 3"). The reviewer depends on MCP tools named `mcp__agents4geos__<tool>`.
- Run tests with `uv run pytest`. The bundled schema cache makes a GEOS build unnecessary.
- Beads issue for this work: `agents4geos-w9k` (already claimed). Epic: `agents4geos-gy9`.

---

### Task 1: Verify the load-bearing assumption (MCP access from a subagent)

The entire design assumes a dispatched subagent can call agents4geos MCP tools and see the shared `DocumentStore`. Prove it before building anything else. This task also creates the subagent file with its **final frontmatter** (the part that grants MCP access) and a temporary diagnostic body.

**Files:**
- Create: `.claude/agents/geos-reviewer.md`

- [ ] **Step 1: Create the branch**

```bash
cd /home/adriano/codes/agents4geos
git checkout -b independent-reviewer
```

- [ ] **Step 2: Create the subagent with final frontmatter + a diagnostic body**

Create `.claude/agents/geos-reviewer.md`:

```markdown
---
name: geos-reviewer
description: Independent fresh-context reviewer of a built GEOS deck. Judges schema validity, cross-references, physics realism, and fidelity to the user's stated intent. Returns structured findings only. Dispatched by the geos orchestrator; not user-invocable.
model: opus
tools: Read, mcp__agents4geos__validate_xml, mcp__agents4geos__load_xml, mcp__agents4geos__validate_cross_references, mcp__agents4geos__sanity_check, mcp__agents4geos__describe_element, mcp__agents4geos__lookup_field_names, mcp__agents4geos__get_cross_references
---

DIAGNOSTIC MODE (temporary — replaced in Task 3).

Call the `health_check` MCP tool, then call `describe_element` with elementName
"SinglePhaseFVM". Return a JSON object:
{ "mcp_accessible": true|false, "health": <health_check output>,
  "described_ok": true|false }
If you cannot call the MCP tools at all, return
{ "mcp_accessible": false } and nothing else.
```

- [ ] **Step 3: Dispatch the subagent to verify MCP access**

Using the Agent tool, dispatch `geos-reviewer` with the prompt: "Run your diagnostic and return the JSON."

Expected: the returned JSON has `"mcp_accessible": true` and a non-empty `health` field, and `"described_ok": true`.

**If `mcp_accessible` is false: STOP.** The design's data flow is invalid. Do not proceed. Re-open the spec and switch the reviewer to a file-only flow (it must `Read` the preview file and rely on `validate_xml(file_path)` only, without shared `DocumentStore` access). Record the finding in `agents4geos-w9k` and ask the user before continuing.

- [ ] **Step 4: Commit the verified frontmatter**

```bash
git add .claude/agents/geos-reviewer.md
git commit -m "feat(review): geos-reviewer subagent frontmatter; verify MCP access from subagent"
```

---

### Task 2: Canonical findings contract (deterministic, TDD)

The reviewer returns findings as JSON. This module is the single source of truth for that shape — used by the eval harness now, and the designed-in sink for a future Dolt table. Pure Python, fully unit-tested.

**Files:**
- Create: `src/agents4geos/review/__init__.py`
- Create: `src/agents4geos/review/findings.py`
- Test: `tests/review/test_findings.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/review/__init__.py` (empty), then `tests/review/test_findings.py`:

```python
import pytest
from agents4geos.review.findings import (
    ReviewFinding, parse_findings, has_blocking, SEVERITIES, CATEGORIES,
)


def test_blocking_severities():
    assert ReviewFinding("error", "schema", "Solvers", "x", "y").is_blocking
    assert ReviewFinding("warning", "xref", "a", "x", "y").is_blocking
    assert not ReviewFinding("advisory", "physics", "a", "x", "y").is_blocking


def test_invalid_severity_rejected():
    with pytest.raises(ValueError):
        ReviewFinding("fatal", "schema", "a", "x", "y")


def test_invalid_category_rejected():
    with pytest.raises(ValueError):
        ReviewFinding("error", "nonsense", "a", "x", "y")


def test_parse_findings_roundtrip():
    items = [{"severity": "error", "category": "intent", "location": "Events",
              "issue": "runs 1 month not 1 year",
              "suggested_fix": "set maxTime=3.15e7", "intent_mismatch": True}]
    fs = parse_findings(items)
    assert len(fs) == 1 and fs[0].intent_mismatch and fs[0].is_blocking


def test_parse_findings_missing_key_raises():
    with pytest.raises(ValueError):
        parse_findings([{"severity": "error", "category": "intent"}])


def test_parse_findings_defaults_intent_mismatch_false():
    items = [{"severity": "advisory", "category": "physics", "location": "a",
              "issue": "x", "suggested_fix": "y"}]
    assert parse_findings(items)[0].intent_mismatch is False


def test_has_blocking():
    advisory = parse_findings([{"severity": "advisory", "category": "physics",
                                "location": "a", "issue": "x", "suggested_fix": "y"}])
    assert not has_blocking(advisory)
    blocking = parse_findings([{"severity": "warning", "category": "xref",
                                "location": "a", "issue": "x", "suggested_fix": "y"}])
    assert has_blocking(blocking)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/review/test_findings.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents4geos.review'`.

- [ ] **Step 3: Implement the module**

Create `src/agents4geos/review/__init__.py` (empty), then `src/agents4geos/review/findings.py`:

```python
"""Canonical contract for geos-reviewer findings.

The geos-reviewer subagent returns a JSON list of findings; this module is the
single source of truth for that shape. Used by the review eval harness now, and
the designed-in sink for a future Dolt errors/lessons table (see
docs/superpowers/specs/2026-06-09-independent-reviewer-subagent-design.md sec.5).
"""
from __future__ import annotations

from dataclasses import dataclass

SEVERITIES = ("error", "warning", "advisory")
CATEGORIES = ("schema", "xref", "physics", "intent")
BLOCKING_SEVERITIES = ("error", "warning")


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    category: str
    location: str
    issue: str
    suggested_fix: str
    intent_mismatch: bool = False

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"invalid severity {self.severity!r}; expected one of {SEVERITIES}"
            )
        if self.category not in CATEGORIES:
            raise ValueError(
                f"invalid category {self.category!r}; expected one of {CATEGORIES}"
            )

    @property
    def is_blocking(self) -> bool:
        return self.severity in BLOCKING_SEVERITIES


def parse_findings(items: list[dict]) -> list[ReviewFinding]:
    """Validate and parse the reviewer's JSON output into ReviewFinding objects.

    Raises ValueError if any item is missing required keys or has an invalid
    severity/category.
    """
    required = {"severity", "category", "location", "issue", "suggested_fix"}
    findings: list[ReviewFinding] = []
    for i, item in enumerate(items):
        missing = required - item.keys()
        if missing:
            raise ValueError(f"finding[{i}] missing keys: {sorted(missing)}")
        findings.append(
            ReviewFinding(
                severity=item["severity"],
                category=item["category"],
                location=item["location"],
                issue=item["issue"],
                suggested_fix=item["suggested_fix"],
                intent_mismatch=item.get("intent_mismatch", False),
            )
        )
    return findings


def has_blocking(findings: list[ReviewFinding]) -> bool:
    """True if any finding is error/warning (drives the orchestrator fix loop)."""
    return any(f.is_blocking for f in findings)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/review/test_findings.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/agents4geos/review/ tests/review/
git commit -m "feat(review): canonical ReviewFinding contract + validator (TDD)"
```

---

### Task 3: Write the real reviewer instructions

Replace the diagnostic body from Task 1 with the full review logic. Frontmatter stays unchanged (already verified).

**Files:**
- Modify: `.claude/agents/geos-reviewer.md` (body only, below the frontmatter)

- [ ] **Step 1: Replace the body**

Keep the frontmatter from Task 1. Replace everything below the closing `---` with:

```markdown
You are an INDEPENDENT reviewer of a GEOS simulation deck. You did not build this
deck and you must not assume anything about how it was built. You see only two
things: the deck artifact and the user's original request. Your job is to find
everything wrong with the deck — especially places where it does not match what
the user actually asked for.

## Inputs you are given
- A preview file path and a `doc_id` for the built deck.
- The user's ORIGINAL request, verbatim. Treat the user's words as ground truth
  for intent.

## What to do
1. `Read` the preview file to see the full XML.
2. `validate_xml(file_path)` — schema validity (structural).
3. `load_xml(file_path)` → `validate_cross_references(doc_id)` — name consistency
   (discretization → NumericalMethods, targetRegions → ElementRegions,
   materialList → Constitutive, setNames → Geometry, *ModelName → Constitutive).
4. `sanity_check(doc_id)` — physics heuristics (perm 1e-20..1e-8 m², porosity
   0.001..0.5, pressure > 0, temperature 273..573 K, compositions sum ~1).
5. **Intent fidelity (the part the tools cannot do):** compare the deck against
   the user's words. Check every quantitative ask:
   - run duration / total time (Events maxTime vs. the user's "for N days/years")
   - injection / production rates and control mode (rate vs BHP, surface vs downhole)
   - which face / location boundary conditions and wells sit on
   - domain dimensions and mesh resolution
   - fluid type / components / salinity / temperature / pressure
   - output cadence (how often VTK is written)
   For each, decide: does the deck match the user's stated value? If not, that is
   an `intent` finding with `intent_mismatch: true`.

## Output — STRUCTURED FINDINGS ONLY
Return a JSON array (and nothing else). Each element:
{
  "severity": "error" | "warning" | "advisory",
  "category": "schema" | "xref" | "physics" | "intent",
  "location": "<section/element path, e.g. Events/PeriodicEvent[name=solverApplications]>",
  "issue": "<what is wrong, concretely>",
  "suggested_fix": "<concrete remedy, e.g. set maxTime=3.15e7 (1 year in s)>",
  "intent_mismatch": true | false
}
Severity rules: `error` = schema violation (GEOS won't load). `warning` = broken
cross-ref / runtime crash. `advisory` = sanity/physics concern OR a minor intent
gap. If the deck is correct and faithful, return `[]`.

Do NOT write prose, explanations, or summaries. Do NOT edit the deck — you have no
editing tools. Return the JSON array only.
```

- [ ] **Step 2: Sanity-check the file parses as valid frontmatter**

Run: `uv run python -c "import re,sys; t=open('.claude/agents/geos-reviewer.md').read(); fm=re.match(r'^---\n(.*?)\n---\n', t, re.S); print('frontmatter OK' if fm and 'model: opus' in fm.group(1) and 'mcp__agents4geos__sanity_check' in fm.group(1) else 'FRONTMATTER BROKEN'); sys.exit(0 if fm else 1)"`
Expected: `frontmatter OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/geos-reviewer.md
git commit -m "feat(review): full geos-reviewer instructions (schema+xref+physics+intent)"
```

---

### Task 4: Review fixtures + deterministic fixture validation

Build fixtures with seeded defects. Two kinds: **tool-catchable** (perm out of range, broken xref) — a pytest asserts the deterministic tools flag them; and **intent-mismatch** (duration/face wrong but schema-valid) — a pytest asserts the deterministic tools DO NOT flag them, proving the LLM reviewer is necessary.

**Files:**
- Create: `tests/fixtures/review/good_single_phase.xml`
- Create: `tests/fixtures/review/manifest.json`
- Test: `tests/review/test_fixtures.py`

- [ ] **Step 1: Generate the known-good base deck**

Using the MCP tools in this session, run `create_document(template="single_phase_flow")`, then `save_xml(doc_id, "<abs>/tests/fixtures/review/good_single_phase.xml")` (use an absolute path via `realpath`). This produces a schema-valid single-phase deck to mutate.

Verify it exists and is non-empty:
Run: `test -s tests/fixtures/review/good_single_phase.xml && echo OK`
Expected: `OK`

- [ ] **Step 2: Create the defect manifest**

Create `tests/fixtures/review/manifest.json`. Each entry describes one fixture: the base file, the exact mutation to apply, the user-intent string, and the expected finding (category + whether the deterministic tools should catch it):

```json
{
  "intent": "single-phase water flow on a 100 m cube, run for 1 year with VTK output monthly",
  "cases": [
    {
      "name": "perm_out_of_range",
      "mutation": "Set the permeability component values in the Constitutive permeability model to 1e-2 (way above the 1e-8 m^2 ceiling).",
      "expect_category": "physics",
      "tool_catchable": true
    },
    {
      "name": "broken_materiallist_ref",
      "mutation": "Change one name in an ElementRegion materialList to a constitutive model name that does not exist (e.g. 'nonexistentRock').",
      "expect_category": "xref",
      "tool_catchable": true
    },
    {
      "name": "duration_mismatch",
      "mutation": "Set Events maxTime to 2.6e6 (about 1 month) while the intent says 1 year. Deck stays schema-valid.",
      "expect_category": "intent",
      "tool_catchable": false
    }
  ]
}
```

- [ ] **Step 3: Create the defect decks by mutation**

For each case in the manifest, copy `good_single_phase.xml` to `tests/fixtures/review/<name>.xml` and apply the described mutation (you may use the MCP `load_xml`/`update_element`/`save_xml` flow, or a precise text edit). Keep mutations minimal — exactly the one defect described.

Verify all four fixtures exist:
Run: `ls tests/fixtures/review/*.xml | wc -l`
Expected: `4`

- [ ] **Step 4: Write the deterministic fixture test**

Create `tests/review/test_fixtures.py`:

```python
"""Validates the review fixtures: tool-catchable defects ARE caught by the
deterministic MCP tools; intent-mismatch defects are NOT (so only the LLM
reviewer can catch them — which is the whole point of geos-reviewer).

Tool return shapes (verified against source 2026-06-09):
  validate_xml(path)               -> {"valid": True|False|None, "errors": [...]}
                                      (None = xmllint not installed)
  load_xml(path)                   -> {"doc_id": "...", ...}
  validate_cross_references(doc)   -> {"valid": bool, "errors": [...]}
  sanity_check(doc)                -> {"checks": [{"status": "fail|advisory|pass",
                                       "message": ...}], "total": int, "failures": int}
These tools are plain callable functions (not FastMCP-wrapped) and share a
module-level DocumentStore, so load_xml then validate/sanity in sequence works.
sanity_check lives in postproc_tools, the rest in xml_tools.
"""
import json
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "review"


def _manifest():
    return json.loads((FIX / "manifest.json").read_text())


@pytest.mark.parametrize("case", _manifest()["cases"], ids=lambda c: c["name"])
def test_fixture_exists_and_is_xml(case):
    p = FIX / f"{case['name']}.xml"
    assert p.exists() and p.read_text().lstrip().startswith("<")


def test_intent_mismatch_passes_deterministic_tools():
    """The duration-mismatch deck must be schema-valid and pass sanity/xref —
    proving the deterministic layer cannot catch intent errors."""
    from agents4geos.tools.xml_tools import (
        load_xml, validate_cross_references, validate_xml,
    )
    from agents4geos.tools.postproc_tools import sanity_check

    deck = str(FIX / "duration_mismatch.xml")
    # schema-valid (True), or None if xmllint absent — must NOT be False
    assert validate_xml(deck)["valid"] is not False
    doc = load_xml(deck)["doc_id"]
    assert validate_cross_references(doc)["errors"] == []
    checks = sanity_check(doc)["checks"]
    assert not any(c["status"] == "fail" for c in checks)
```

- [ ] **Step 5: Run the deterministic fixture test**

Run: `uv run pytest tests/review/test_fixtures.py -q`
Expected: PASS. If `test_intent_mismatch_passes_deterministic_tools` fails because a tool DOES flag the duration deck, your mutation accidentally broke schema/xref — re-make `duration_mismatch.xml` so it is schema-valid and only semantically wrong.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/review/ tests/review/test_fixtures.py
git commit -m "test(review): seeded-defect fixtures + deterministic validation"
```

---

### Task 5: Eval runbook for the LLM reviewer (agent-run recall)

The reviewer's judgment (especially intent-mismatch recall) can't be unit-tested. Document a repeatable agent-run eval that scores recall against the fixtures.

**Files:**
- Create: `tests/review/RUNBOOK.md`

- [ ] **Step 1: Write the runbook**

Create `tests/review/RUNBOOK.md`:

```markdown
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

## Record results
Append a dated results block to this file each run (date, per-case caught/missed),
so reviewer-instruction changes can be compared over time.
```

- [ ] **Step 2: Run the eval once and record a baseline**

Execute the runbook against all fixtures now. Append a dated results block to `RUNBOOK.md` with caught/missed per case. If `duration_mismatch` is missed, refine the reviewer body (Task 3 file) and re-run before proceeding.

- [ ] **Step 3: Commit**

```bash
git add tests/review/RUNBOOK.md
git commit -m "test(review): reviewer eval runbook + baseline results"
```

---

### Task 6: Wire the Independent Review Gate into the orchestrator

**Files:**
- Modify: `skills/geos.md` (add a Stage R section; route the creation flow through it)

- [ ] **Step 1: Add the Stage R section**

In `skills/geos.md`, immediately AFTER the `## Workflow` section (before `## CRITICAL: Template vs Add/Update Rules`), insert:

```markdown
## Stage R — Independent Review Gate (creation flow, before save_xml)

After the deck is assembled and previewed, BEFORE `save_xml` and before presenting
to the user, run an independent review. The reviewer runs in a FRESH context — it
knows only the artifact and the user's words, not how you built the deck. That
independence is the point; do not try to explain your choices to it.

1. Ensure a current preview exists (`preview_xml(doc_id)` → path) and you know the
   `doc_id`.
2. Dispatch the `geos-reviewer` subagent (Agent tool) with:
   - the preview file absolute path AND the `doc_id`,
   - the user's ORIGINAL request, VERBATIM (do not paraphrase — the reviewer
     judges intent fidelity against the user's exact words),
   - the workspace absolute path so it can resolve files.
3. It returns a JSON array of findings
   (severity/category/location/issue/suggested_fix/intent_mismatch).
4. **Fix loop (max 3 iterations):**
   - If any finding has severity `error` or `warning` (blocking): fix each via
     `update_element`/`add_element`/`add_child`/`remove_element`, then
     `preview_xml` again and dispatch a FRESH `geos-reviewer`.
   - Stop when no blocking findings remain, or after 3 iterations.
5. **On clean:** `save_xml`, then present the deck. Briefly mention any remaining
   `advisory` findings.
6. **On non-convergence (still blocking after 3 iterations):** do NOT hide it.
   Save the best version, present it, and tell the user honestly: "My independent
   reviewer still flags these issues I could not fully resolve: <list them>."
   NEVER silently present a deck the reviewer rejected.
```

- [ ] **Step 2: Route the creation flow through the gate**

In `skills/geos.md`, find the creation-flow line (currently around line 133):

```
   - `validate_cross_references` → `sanity_check` → `preview_xml` → `save_xml`.
```

Replace it with:

```
   - `validate_cross_references` → `sanity_check` → `preview_xml` → **Stage R
     (Independent Review Gate, see below)** → `save_xml`.
```

- [ ] **Step 3: Verify the edits are present and consistent**

Run: `grep -c "Stage R" skills/geos.md`
Expected: `2` (the section header + the workflow reference).

- [ ] **Step 4: Commit**

```bash
git add skills/geos.md
git commit -m "feat(review): wire Independent Review Gate + bounded fix loop into orchestrator"
```

---

### Task 7: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md` (taxonomy note in §1; registry entry in §3; coordination in §6)

- [ ] **Step 1: Add the taxonomy note (§1)**

In `AGENTS.md`, immediately after the taxonomy table's "Key distinction" line, add:

```markdown
**Note (2026-06-09):** Agents now come in two forms — *prompt-overlay skills*
(`skills/geos:*.md`, loaded into the main conversation, same context/model) and
*real subagents* (`.claude/agents/*.md`, dispatched via the Agent tool with their
own context and `model:`). `geos-reviewer` is the first real subagent.
```

- [ ] **Step 2: Add the registry entry (§3)**

In `AGENTS.md` §3, after the `geos:curate-errors` entry, add:

```markdown
**`geos-reviewer`** (Independent Reviewer subagent) — Tier 3
- *Description:* Fresh-context independent review of a built deck — schema,
  cross-refs, physics realism, and fidelity to the user's stated intent.
  Dispatched automatically by `geos` before save; NOT user-invocable.
- *Type:* Real Claude Code subagent (`.claude/agents/geos-reviewer.md`,
  `model: opus`), dispatched via the Agent tool — not a slash-command skill.
- *Tools:* read/validate MCP tools only (`validate_xml`, `load_xml`,
  `validate_cross_references`, `sanity_check`, `describe_element`,
  `lookup_field_names`, `get_cross_references`) + `Read`. No deck-editing tools —
  it judges, it does not mutate.
- *Knowledge:* `sanity_rules`, `cross_refs`, `field_names` (indirectly via tools)
- *Inputs:* artifact (preview path + doc_id) + the user's original request verbatim
- *Outputs:* structured findings JSON
  (severity/category/location/issue/suggested_fix/intent_mismatch)
- *Coordination:* feedback loop — `geos` builds → `geos-reviewer` reviews → `geos`
  fixes → re-review, bounded at 3 iterations
```

- [ ] **Step 3: Mark the feedback-loop pattern realized (§6)**

In `AGENTS.md` §6 "Feedback loop", change the `*Anticipated example:*` line to add a realized example directly above it:

```markdown
*Current example (2026-06-09):* `geos` builds a deck → `geos-reviewer`
independently reviews it (fresh context) → if blocking findings, `geos` fixes and
re-dispatches a fresh reviewer, bounded at 3 iterations.
```

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): register geos-reviewer; mark feedback-loop pattern realized"
```

---

### Task 8: End-to-end scenario + finish

**Files:** none (verification + housekeeping)

- [ ] **Step 1: Full-suite regression**

Run: `uv run pytest tests/ -q`
Expected: all green (the existing 191 + the new review tests).

- [ ] **Step 2: Curated end-to-end scenario**

In a workspace with the MCP server registered, run a real `/geos` creation request whose intent has a number the builder might get wrong, e.g.:
"/geos single-phase water flow on a 100 m cube, run for **1 year**, VTK output monthly."
Confirm the orchestrator dispatches `geos-reviewer` before saving, and that if any blocking/intent finding appears it enters the fix loop and reports honestly. Note the observed behavior in `tests/review/RUNBOOK.md` results.

- [ ] **Step 3: Push and open a PR**

```bash
git push -u origin independent-reviewer
gh pr create --title "Independent reviewer subagent + bounded fix loop" --body "First real subagent (.claude/agents/geos-reviewer.md, model: opus). Orchestrator dispatches it after build to catch schema/xref/physics AND intent-mismatch the inline tools miss, then runs a bounded (max 3) fix loop with honest non-convergence reporting. Canonical findings contract in src/agents4geos/review/findings.py (Dolt-ready). Spec + plan under docs/superpowers/. Implements agents4geos-w9k."
```

- [ ] **Step 4: Close the beads issue and push state**

```bash
bd close agents4geos-w9k --reason="Independent reviewer subagent + bounded fix loop implemented on branch independent-reviewer (PR opened)"
bd dolt push
```

---

## Notes for the executor

- **Task 1 is a hard gate.** If MCP access from the subagent fails, the rest of the
  plan's data flow is wrong — stop and consult the user.
- The reviewer must stay **judge-not-mutate**: no editing tools in its allowlist.
  The orchestrator does all fixing.
- Keep fixture mutations **minimal and singular** — one seeded defect per file, or
  the eval can't attribute recall.
- The findings JSON schema is the **Dolt seam** (spec §5). Do not change its keys
  casually — a future task writes these rows to a Dolt errors/lessons table.
- Tests: `uv run pytest`. The bundled schema cache means no GEOS build is needed.
