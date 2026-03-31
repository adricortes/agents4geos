# Runtime Error Logging — Design Spec

## Problem

GEOS runtime errors reveal solver/constitutive compatibility rules that are not
in the XSD schema and only discoverable at runtime. Today the agent rediscovers
these rules every session (e.g., `ImmiscibleMultiphaseFlow` requires
`TwoPhaseImmiscibleFluid`, not `InvariantImmiscibleFluid`). Each failure costs
multiple tool calls and re-runs.

## Solution: Two-Layer Error Knowledge

### Layer 1 — Raw Error Log (per-user, gitignored)

**File:** `knowledge/runtime_errors.jsonl`

One JSON object per line, appended by an MCP tool after each failed GEOS run:

```jsonl
{
  "timestamp": "2026-03-31T14:23:00Z",
  "xml_file": "inverted_gravity_column.xml",
  "solvers": ["ImmiscibleMultiphaseFlow"],
  "constitutive_types": ["InvariantImmiscibleFluid", "BrooksCoreyRelativePermeability", "CompressibleSolidConstantPermeability"],
  "geos_error": "***** ABORT [ImmiscibleMultiphaseFlow]: constitutive model not found",
  "error_summary": "ImmiscibleMultiphaseFlow requires TwoPhaseImmiscibleFluid, not InvariantImmiscibleFluid",
  "fix_applied": "Replaced InvariantImmiscibleFluid with TwoPhaseImmiscibleFluid using TableFunction references"
}
```

**Fields:**

| Field | Source | Required |
|---|---|---|
| `timestamp` | Auto-generated (UTC ISO 8601) | Yes |
| `xml_file` | Extracted from document state | Yes |
| `solvers` | Extracted from document Solvers section | Yes |
| `constitutive_types` | Extracted from document Constitutive section | Yes |
| `geos_error` | Raw GEOS error text (agent provides) | Yes |
| `error_summary` | Agent's one-line diagnosis | Yes |
| `fix_applied` | What resolved the issue, or `"UNRESOLVED"` | Yes |

### Layer 2 — Curated Lessons (shared, checked into repo)

**File:** `knowledge/lessons_learned.md`

Structured Markdown that agents read before making solver/constitutive decisions.

**Lesson template:**

```markdown
### <Short rule title>
- **Wrong:** <what the agent did that caused the failure>
- **Right:** <what GEOS actually needs>
- **Pattern:**
  ```xml
  <correct XML snippet>
  ```
- **Source:** <the GEOS error message>
```

**Section structure:**

```markdown
# GEOS Runtime Lessons Learned

Read this file BEFORE choosing solver/constitutive combinations or setting up
FieldSpecifications. Each lesson documents a real runtime failure and the
correct pattern to avoid it.

## Solver-Constitutive Compatibility
(rules about which solver requires which constitutive type)

## FieldSpecification Rules
(rules about fieldName choices per solver type)

## NumericalMethods Rules
(rules about element nesting and naming)

## Mesh and Geometry Rules
(rules about geometry boxes, cell centers, etc.)
```

## MCP Tool: `log_runtime_error`

**Location:** `tools/xml_tools.py` (alongside other document-aware tools)

**Signature:**

```python
@mcp.tool
def log_runtime_error(
    doc_id: str,
    geos_error: str,
    error_summary: str,
    fix_applied: str,
) -> dict:
```

**Behavior:**

1. Look up the document by `doc_id` to extract:
   - `xml_file`: from the document's file path (or "unknown" if unsaved)
   - `solvers`: element type names from the Solvers section
   - `constitutive_types`: element type names from the Constitutive section
2. Build the JSONL entry with auto-generated UTC timestamp
3. Append to `knowledge/runtime_errors.jsonl` (create if missing)
4. Return the logged entry for confirmation

**Returns:**

```python
{"logged": True, "entry": { ... }, "log_file": "knowledge/runtime_errors.jsonl"}
```

## Skill Updates

### `geos:run` — Updated Workflow

Remove the hardcoded "common issues" list (current lines 21-24). Replace with:

```markdown
## Before Running

Read `knowledge/lessons_learned.md` to check for known solver/constitutive
compatibility rules that apply to your XML.

## After a Failed Run

If `geosx -i` exits with a non-zero code:
1. Diagnose and fix the issue
2. Re-run to confirm the fix works
3. Call `log_runtime_error` with the full context: the GEOS error text,
   your one-line diagnosis, and what fix resolved it

If the fix fails after 3 attempts, call `log_runtime_error` anyway with
fix_applied="UNRESOLVED" so the error is captured for future curation.

This logging step is NOT optional. It captures your understanding of what
went wrong while the context is fresh.
```

### New Skill: `geos:curate-errors`

**File:** `skills/geos:curate-errors.md`

**Behavior:**

1. Read `knowledge/runtime_errors.jsonl`
2. Group by `error_summary` to find duplicates
3. For each unique error not already in `lessons_learned.md`:
   - Propose a new lesson entry using the template
4. Present proposed additions to the user for review
5. On approval, append to `lessons_learned.md`

## Seed Content for `lessons_learned.md`

Migrated from the current `geos:run` skill plus today's session:

1. **Coupled solid required in materialList** (from existing tip)
2. **Geometry box must enclose cell centers** (from existing tip)
3. **Component fractions must sum to 1** (from existing tip)
4. **ImmiscibleMultiphaseFlow requires TwoPhaseImmiscibleFluid** (today)
5. **ImmiscibleMultiphaseFlow uses phaseVolumeFraction, not globalCompFraction** (today)

## .gitignore Update

Add `knowledge/runtime_errors.jsonl` to `.gitignore`.

## Testing

- Unit test for `log_runtime_error`: create a document, call the tool, verify
  JSONL file is created with correct fields
- Unit test for extraction: verify solver/constitutive types are correctly
  pulled from document state
- Manual test: run `/geos:run` with a known-bad XML, verify the agent logs
  the error after fixing it
