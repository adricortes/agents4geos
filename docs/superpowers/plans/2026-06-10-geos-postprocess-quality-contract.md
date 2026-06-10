# geos-postprocess Quality Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `geos:postprocess` into a real dispatched subagent (`geos-postprocess`) that enforces a publication-quality figure contract — Crameri scientific colormaps, SI-unit titles, rainbow/`jet` banned — at both the prompt layer and a code seam, while keeping the `/geos:postprocess` slash command (cw7 "keep both" pattern).

**Architecture:** A new `tools/colormaps.py` policy module registers Crameri maps (via `cmcrameri`) and rejects/steers perceptually non-uniform maps. `screenshot_field` adopts `cmc.batlow` as its default and guards against banned maps. A new `PostprocessResult` contract in `dispatch/results.py` validates the subagent's structured output and **fails validation on a banned colormap** (the code seam). The `.claude/agents/geos-postprocess.md` subagent encodes the MUST-level contract; `skills/geos:postprocess.md` is hardened to the same standard; `skills/geos:run.md` dispatches the subagent after a successful run with an inline fallback.

**Tech Stack:** Python 3.11, PyVista (core), matplotlib (transitive via PyVista), `cmcrameri` (new core dep), pytest, FastMCP. Spec: `docs/superpowers/specs/2026-06-10-tnt-subagent-conversion-decisions-design.md`.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `pyproject.toml` | Add `cmcrameri` to core `dependencies` | Modify |
| `src/agents4geos/tools/colormaps.py` | Scientific colormap policy: defaults, banned set, `resolve_colormap()`, cmc registration | Create |
| `tests/test_colormaps.py` | Unit tests for the policy module | Create |
| `src/agents4geos/tools/postproc_tools.py` | `screenshot_field` default → `cmc.batlow`; guard via `resolve_colormap` | Modify |
| `tests/test_postproc_tools.py` | Banned-map guard + default-value tests | Modify |
| `src/agents4geos/dispatch/results.py` | `FieldStat`, `FigureRef`, `PostprocessResult`, `parse_postprocess_result` | Modify |
| `tests/dispatch/test_results.py` | Contract parse/validation tests | Modify |
| `.claude/agents/geos-postprocess.md` | The MUST-level subagent contract | Create |
| `skills/geos:postprocess.md` | Harden slash-command standard to match | Modify |
| `skills/geos:run.md` | Dispatch `geos-postprocess` after a successful run (inline fallback) | Modify |
| `AGENTS.md` | §3 registry entry + §6 coordination note | Modify |
| `tests/dispatch/RUNBOOK.md` | Live-gate entry (PENDING if headless) | Modify |

---

### Task 1: Scientific colormap policy module

**Files:**
- Modify: `pyproject.toml:6-11`
- Create: `src/agents4geos/tools/colormaps.py`
- Test: `tests/test_colormaps.py`

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, change the core `dependencies` list (lines 6-11) to add `cmcrameri`:

```toml
dependencies = [
    "fastmcp>=2.0",
    "lxml>=5.0",
    "pyvista>=0.43",
    "numpy>=1.24",
    "cmcrameri>=1.4",
]
```

- [ ] **Step 2: Install it**

Run: `uv sync --all-extras`
Expected: resolves and installs `cmcrameri` (pulls matplotlib if not already present via pyvista).

- [ ] **Step 3: Write the failing test**

Create `tests/test_colormaps.py`:

```python
import matplotlib
import pytest

from agents4geos.tools.colormaps import (
    SEQUENTIAL_DEFAULT, DIVERGING_DEFAULT, CYCLIC_DEFAULT,
    BANNED_COLORMAPS, resolve_colormap,
)


def test_scientific_defaults_are_crameri():
    assert SEQUENTIAL_DEFAULT == "cmc.batlow"
    assert DIVERGING_DEFAULT == "cmc.vik"
    assert CYCLIC_DEFAULT == "cmc.romaO"


def test_crameri_maps_registered_with_matplotlib():
    # cmcrameri registers cmc.* maps on import; resolve must surface usable names.
    assert matplotlib.colormaps[resolve_colormap(SEQUENTIAL_DEFAULT)] is not None
    assert matplotlib.colormaps[resolve_colormap(DIVERGING_DEFAULT)] is not None


def test_banned_maps_listed():
    assert "jet" in BANNED_COLORMAPS
    assert "rainbow" in BANNED_COLORMAPS
    assert "hsv" in BANNED_COLORMAPS


def test_resolve_rejects_banned_strict():
    with pytest.raises(ValueError):
        resolve_colormap("jet")


def test_resolve_steers_banned_nonstrict():
    # non-strict steers jet -> scientific diverging, never returns the banned name
    out = resolve_colormap("jet", strict=False)
    assert out not in BANNED_COLORMAPS
    assert out == DIVERGING_DEFAULT


def test_resolve_passes_through_safe_map():
    assert resolve_colormap("viridis") == "viridis"
```

- [ ] **Step 4: Run it to verify it fails**

Run: `uv run pytest tests/test_colormaps.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents4geos.tools.colormaps'`.

- [ ] **Step 5: Write the module**

Create `src/agents4geos/tools/colormaps.py`:

```python
"""Scientific colormap policy for publication-quality field figures.

Crameri Scientific Colour Maps are perceptually uniform, colour-blind-safe, and
readable in grayscale — the publication standard. The `cmcrameri` package
registers them with matplotlib (as `cmc.*`) on import. Rainbow/`jet`-family maps
are perceptually non-uniform and are rejected. See
docs/superpowers/specs/2026-06-10-tnt-subagent-conversion-decisions-design.md.
"""
from __future__ import annotations

# Data-type-aware scientific defaults (registered as cmc.* by cmcrameri).
SEQUENTIAL_DEFAULT = "cmc.batlow"
DIVERGING_DEFAULT = "cmc.vik"
CYCLIC_DEFAULT = "cmc.romaO"

# Perceptually non-uniform / not grayscale-robust — never publish these.
BANNED_COLORMAPS = frozenset(
    {"jet", "rainbow", "hsv", "gist_rainbow", "nipy_spectral"}
)

# Steering map: banned name -> scientific replacement (used in non-strict mode).
_STEER = {
    "jet": DIVERGING_DEFAULT,
    "rainbow": DIVERGING_DEFAULT,
    "gist_rainbow": DIVERGING_DEFAULT,
    "hsv": CYCLIC_DEFAULT,
    "nipy_spectral": SEQUENTIAL_DEFAULT,
}


def _register_crameri() -> bool:
    """Import cmcrameri to register the cmc.* colormaps. True if available."""
    try:
        import cmcrameri.cm  # noqa: F401  (import side-effect registers cmc.* maps)
        return True
    except ImportError:
        return False


_CMC_AVAILABLE = _register_crameri()


def resolve_colormap(name: str, *, strict: bool = True) -> str:
    """Return a publication-safe colormap name.

    - Banned (non-uniform) maps raise ValueError in strict mode, or are steered to
      a scientific equivalent in non-strict mode.
    - A `cmc.*` name falls back to a matplotlib perceptually-uniform builtin if the
      `cmcrameri` package is unavailable, so a missing dep never blocks a figure.
    """
    if name in BANNED_COLORMAPS:
        if strict:
            raise ValueError(
                f"colormap {name!r} is perceptually non-uniform / not "
                f"grayscale-safe; use a scientific map (e.g. "
                f"{SEQUENTIAL_DEFAULT} sequential / {DIVERGING_DEFAULT} diverging)"
            )
        name = _STEER[name]
    if name.startswith("cmc.") and not _CMC_AVAILABLE:
        return "viridis" if name != DIVERGING_DEFAULT else "RdBu_r"
    return name
```

- [ ] **Step 6: Run it to verify it passes**

Run: `uv run pytest tests/test_colormaps.py -v`
Expected: PASS (6 passed).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/agents4geos/tools/colormaps.py tests/test_colormaps.py
git commit -m "feat(postproc): scientific colormap policy + cmcrameri dep (tnt)"
```

---

### Task 2: `screenshot_field` adopts the policy

**Files:**
- Modify: `src/agents4geos/tools/postproc_tools.py:52-71,100-103`
- Test: `tests/test_postproc_tools.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_postproc_tools.py`:

```python
import inspect
import pytest
from agents4geos.tools import postproc_tools
from agents4geos.tools.colormaps import SEQUENTIAL_DEFAULT


def test_screenshot_default_is_scientific_not_coolwarm():
    sig = inspect.signature(postproc_tools.screenshot_field)
    assert sig.parameters["colormap"].default == SEQUENTIAL_DEFAULT


def test_screenshot_rejects_banned_colormap_before_render(tmp_path):
    # A banned map must raise at the guard, before any PyVista I/O — so a
    # non-existent file path is fine; the ValueError fires first.
    with pytest.raises(ValueError):
        postproc_tools.screenshot_field(
            file_path=str(tmp_path / "nope.vtu"),
            field_name="pressure",
            colormap="jet",
        )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_postproc_tools.py -k "scientific or banned" -v`
Expected: FAIL — default is still `"coolwarm"`; banned map not guarded.

- [ ] **Step 3: Modify `screenshot_field`**

In `src/agents4geos/tools/postproc_tools.py`, add the import near the top of the file (with the other module-level imports):

```python
from agents4geos.tools.colormaps import SEQUENTIAL_DEFAULT, resolve_colormap
```

Change the signature default (line 56) from `colormap: str = "coolwarm",` to:

```python
    colormap: str = SEQUENTIAL_DEFAULT,
```

Update the docstring line (70) to:

```python
        colormap: Scientific colormap. Default cmc.batlow (perceptually uniform,
            colour-blind-safe). Pass cmc.vik for diverging fields. jet/rainbow are
            rejected.
```

Immediately after `import pyvista as pv` inside the function body (line 75), add the guard so it raises before any file I/O:

```python
    colormap = resolve_colormap(colormap, strict=True)
```

(Leave the `cmap=colormap` usage at line 101 unchanged — it now receives a vetted name.)

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_postproc_tools.py -k "scientific or banned" -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full postproc test module to check for regressions**

Run: `uv run pytest tests/test_postproc_tools.py -v`
Expected: PASS (all prior tests still green; the guard rejects only banned maps).

- [ ] **Step 6: Commit**

```bash
git add src/agents4geos/tools/postproc_tools.py tests/test_postproc_tools.py
git commit -m "feat(postproc): screenshot_field defaults to cmc.batlow, bans rainbow/jet (tnt)"
```

---

### Task 3: `PostprocessResult` contract

**Files:**
- Modify: `src/agents4geos/dispatch/results.py` (append new dataclasses + parser)
- Test: `tests/dispatch/test_results.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/dispatch/test_results.py`:

```python
from agents4geos.dispatch.results import (
    PostprocessResult, FieldStat, FigureRef, parse_postprocess_result,
)


def _postproc_dict():
    return {
        "fields": [
            {"name": "pressure", "min": 1.0e6, "max": 2.0e7,
             "mean": 1.1e7, "std": 3.0e6, "units": "Pa"}
        ],
        "figures": [
            {"path": "/abs/pressure.png", "title": "Pressure at t = 1 yr [Pa]",
             "units": "Pa", "colormap": "cmc.vik", "map_type": "diverging"}
        ],
        "derived": {"material_balance_m3": 1.2e5},
        "notes": "final timestep",
    }


def test_parse_postprocess_roundtrip():
    pr = parse_postprocess_result(_postproc_dict())
    assert isinstance(pr, PostprocessResult)
    assert isinstance(pr.fields[0], FieldStat)
    assert pr.fields[0].units == "Pa"
    assert isinstance(pr.figures[0], FigureRef)
    assert pr.figures[0].map_type == "diverging"
    assert pr.derived["material_balance_m3"] == 1.2e5


def test_postproc_field_missing_stat_key_raises():
    d = _postproc_dict(); del d["fields"][0]["std"]
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_figure_missing_path_raises():
    d = _postproc_dict(); del d["figures"][0]["path"]
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_banned_colormap_fails_validation():
    d = _postproc_dict(); d["figures"][0]["colormap"] = "jet"
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_bad_map_type_raises():
    d = _postproc_dict(); d["figures"][0]["map_type"] = "rainbowish"
    with pytest.raises(ValueError):
        parse_postprocess_result(d)


def test_postproc_defaults_when_optional_absent():
    d = _postproc_dict(); del d["derived"]; del d["notes"]
    pr = parse_postprocess_result(d)
    assert pr.derived == {}
    assert pr.notes == ""
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/dispatch/test_results.py -k postproc -v`
Expected: FAIL — `ImportError: cannot import name 'PostprocessResult'`.

- [ ] **Step 3: Implement the contract**

Append to `src/agents4geos/dispatch/results.py` (after the existing parsers). Add this import at the top of the file with the other imports:

```python
from agents4geos.tools.colormaps import BANNED_COLORMAPS
```

Then append:

```python
MAP_TYPES = ("sequential", "diverging", "cyclic")
_FIELD_STAT_KEYS = ("name", "min", "max", "mean", "std", "units")
_FIGURE_KEYS = ("path", "title", "colormap", "map_type")


@dataclass(frozen=True)
class FieldStat:
    name: str
    min: float
    max: float
    mean: float
    std: float
    units: str


@dataclass(frozen=True)
class FigureRef:
    path: str
    title: str
    colormap: str
    map_type: str
    units: str = ""


@dataclass(frozen=True)
class PostprocessResult:
    fields: list[FieldStat]
    figures: list[FigureRef]
    derived: dict = field(default_factory=dict)
    notes: str = ""


def parse_postprocess_result(d: dict) -> PostprocessResult:
    """Validate and parse a geos-postprocess JSON result.

    Enforces the publication contract in code: every figure must declare a valid
    map_type and a non-banned colormap. Raises ValueError on any bad shape.
    """
    for key in ("fields", "figures"):
        if not isinstance(d.get(key), list):
            raise ValueError(f"PostprocessResult '{key}' must be a list")

    stats: list[FieldStat] = []
    for i, f in enumerate(d["fields"]):
        missing = set(_FIELD_STAT_KEYS) - f.keys()
        if missing:
            raise ValueError(f"fields[{i}] missing keys: {sorted(missing)}")
        stats.append(FieldStat(
            f["name"], f["min"], f["max"], f["mean"], f["std"], f["units"],
        ))

    figs: list[FigureRef] = []
    for i, g in enumerate(d["figures"]):
        missing = set(_FIGURE_KEYS) - g.keys()
        if missing:
            raise ValueError(f"figures[{i}] missing keys: {sorted(missing)}")
        if g["colormap"] in BANNED_COLORMAPS:
            raise ValueError(
                f"figures[{i}] colormap {g['colormap']!r} is banned "
                f"(non-uniform); use a scientific map"
            )
        if g["map_type"] not in MAP_TYPES:
            raise ValueError(
                f"figures[{i}] invalid map_type {g['map_type']!r}; "
                f"expected one of {MAP_TYPES}"
            )
        figs.append(FigureRef(
            g["path"], g["title"], g["colormap"], g["map_type"],
            g.get("units", ""),
        ))

    return PostprocessResult(
        fields=stats,
        figures=figs,
        derived=d.get("derived", {}),
        notes=d.get("notes", ""),
    )
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/dispatch/test_results.py -k postproc -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full dispatch test module**

Run: `uv run pytest tests/dispatch/ -v`
Expected: PASS (existing mesh/fluid tests + new postproc tests all green).

- [ ] **Step 6: Commit**

```bash
git add src/agents4geos/dispatch/results.py tests/dispatch/test_results.py
git commit -m "feat(dispatch): PostprocessResult contract enforces colormap policy (tnt)"
```

---

### Task 4: The `geos-postprocess` subagent contract

**Files:**
- Create: `.claude/agents/geos-postprocess.md`

- [ ] **Step 1: Write the agent definition**

Create `.claude/agents/geos-postprocess.md` (mirror the `geos-mesh.md`/`geos-fluids.md` frontmatter style):

```markdown
---
name: geos-postprocess
description: Analyze GEOS VTK output and produce publication-quality figures + field statistics, returned as structured JSON. Tier-2 compute-and-return subagent dispatched by the geos orchestrator after a successful run; not user-invocable.
model: sonnet
tools: Read, mcp__agents4geos__read_vtk_output, mcp__agents4geos__extract_field, mcp__agents4geos__screenshot_field, mcp__agents4geos__compare_timesteps, mcp__agents4geos__compute_darcy_velocity, mcp__agents4geos__compute_material_balance, mcp__agents4geos__compute_well_performance, mcp__agents4geos__sanity_check
---

You are the `geos-postprocess` compute subagent. You ANALYZE GEOS VTK output and
RETURN structured JSON. You do not edit any document — you have no editing tools.

## Inputs you are given
- One or more absolute VTK file paths (final timestep, and/or a time series).
- The fields of interest (or "all"), and the workspace absolute path.

## What to do
1. `read_vtk_output` FIRST on each file to discover available fields and ranges.
2. `extract_field` for per-field statistics (min/max/mean/std).
3. For each field the user cares about, produce a figure with `screenshot_field`.
4. Add derived quantities when relevant: `compute_darcy_velocity`,
   `compute_material_balance`, `compute_well_performance`. Time series →
   `compare_timesteps`.

## PUBLICATION CONTRACT — these are MUST, not suggestions
- **Title:** every figure's `title` MUST end with the SI unit in brackets, e.g.
  `"Pressure at t = 1 yr [Pa]"`, `"Gas saturation [-]"`, `"ΔPressure [Pa]"`.
- **Colormap by data type** (Crameri scientific maps, perceptually uniform &
  colour-blind-safe):
  - Sequential field (saturation, porosity, concentration, pressure magnitude,
    density) → `cmc.batlow`.
  - Diverging field (Δ between timesteps, signed velocity, anomaly about a
    centre) → `cmc.vik`.
  - Cyclic field (phase/angle) → `cmc.romaO`.
- **Forbidden:** `jet`, `rainbow`, `hsv`, and `coolwarm` as a default. Never pass
  these — the tool and the result contract both reject them.
- Use SI units throughout (Pa, m³/s, K, m²).

## Output — STRUCTURED JSON ONLY
Return one JSON object (and nothing else):
{
  "fields": [
    {"name": "pressure", "min": 1.0e6, "max": 2.0e7, "mean": 1.1e7,
     "std": 3.0e6, "units": "Pa"}
  ],
  "figures": [
    {"path": "<absolute png path>", "title": "Pressure at t = 1 yr [Pa]",
     "units": "Pa", "colormap": "cmc.vik", "map_type": "diverging"}
  ],
  "derived": { "material_balance_m3": 1.2e5 },
  "notes": "<which timestep, any caveats>"
}
`map_type` must be one of sequential | diverging | cyclic. Use `derived: {}` and
`figures: []` when empty. Do NOT write prose outside the JSON. Do NOT edit the deck.
```

- [ ] **Step 2: Verify the frontmatter parses**

Run: `uv run python -c "import yaml,io; t=open('.claude/agents/geos-postprocess.md').read(); fm=t.split('---')[1]; d=yaml.safe_load(fm); print(d['name'], d['model']); assert d['name']=='geos-postprocess' and d['model']=='sonnet'"`
Expected: prints `geos-postprocess sonnet` with no assertion error. (If PyYAML is absent, instead eyeball that the frontmatter has matching `---` fences, a `name:`, a `model:`, and a single-line `tools:`.)

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/geos-postprocess.md
git commit -m "feat(agents): geos-postprocess subagent with publication-quality contract (tnt)"
```

---

### Task 5: Harden the slash command

**Files:**
- Modify: `skills/geos:postprocess.md`

- [ ] **Step 1: Replace the colormap guidance with the contract**

In `skills/geos:postprocess.md`, replace the existing two paragraphs that start
with `Default colormap is \`coolwarm\`` (the last block under "## Publication-Quality Screenshots") with:

```markdown
## Colormap contract (publication-quality, REQUIRED)
Choose the colormap by data type — Crameri scientific maps only (perceptually
uniform, colour-blind-safe, grayscale-readable):
- **Sequential** (saturation, porosity, concentration, pressure magnitude,
  density) → `cmc.batlow`
- **Diverging** (Δ fields, signed velocity, anomaly about a centre) → `cmc.vik`
- **Cyclic** (phase/angle) → `cmc.romaO`

NEVER use `jet`, `rainbow`, `hsv`, or `coolwarm`-as-default — they are
perceptually non-uniform and `screenshot_field` rejects them.
```

- [ ] **Step 2: Elevate the title rule to a MUST**

In the same file, change the line `ALWAYS provide a descriptive \`title\` parameter, e.g.:` to:

```markdown
REQUIRED: every figure's `title` MUST end with the SI unit in brackets, e.g.:
```

- [ ] **Step 3: Verify no stale `coolwarm` default guidance remains**

Run: `grep -n "coolwarm\|jet\|cmc\." skills/geos:postprocess.md`
Expected: `coolwarm` and `jet` appear ONLY inside the "NEVER use" banned list; `cmc.batlow`/`cmc.vik`/`cmc.romaO` appear as the recommended maps.

- [ ] **Step 4: Commit**

```bash
git add skills/geos:postprocess.md
git commit -m "docs(skills): harden geos:postprocess colormap+title to a contract (tnt)"
```

---

### Task 6: Wire the orchestrator + update AGENTS.md

**Files:**
- Modify: `skills/geos:run.md:42-54`
- Modify: `AGENTS.md` (§3 registry ~line 120-125; §6 coordination ~line 315-318)

- [ ] **Step 1: Dispatch the subagent after a successful run**

In `skills/geos:run.md`, replace the "## After a Successful Run" section's step 2
("Analyze with MCP tools…") with a dispatch + inline fallback:

```markdown
2. **Dispatch the `geos-postprocess` subagent** (Agent tool) with the absolute
   VTK path(s), the fields of interest, and the workspace path. It returns a
   `PostprocessResult` JSON (field stats + publication-quality figures with
   Crameri colormaps + derived quantities). Surface its figures and stats to the
   user.
   - **Inline fallback:** if the subagent errors or returns an invalid result,
     analyze inline yourself with the MCP tools — `read_vtk_output` →
     `extract_field` → `screenshot_field` (default `cmc.batlow`; pass `cmc.vik`
     for diverging fields; titles end in the SI unit) → `compute_darcy_velocity`
     / `compare_timesteps`. A subagent failure NEVER blocks post-processing.
```

- [ ] **Step 2: Update the "Tips" note that mentions screenshots**

In the same file, change the last Tips bullet (`Always provide a descriptive \`title\`…`) to:

```markdown
- Figures must use a Crameri scientific colormap (`cmc.batlow` sequential /
  `cmc.vik` diverging) and a title ending in the SI unit, e.g. "Pressure at
  t=1yr [Pa]". jet/rainbow are rejected.
```

- [ ] **Step 3: Add the registry entry to AGENTS.md §3**

In `AGENTS.md`, after the `geos-fluids` subagent entry (the block ending around
line 180), add:

```markdown
**`geos-postprocess`** (Post-run analysis subagent) — Tier 2
- *Description:* Analyze GEOS VTK output — field statistics + publication-quality
  figures + derived quantities; return structured JSON. Dispatched by `geos` after
  a successful run; NOT user-invocable (the `/geos:postprocess` slash command
  remains for direct use).
- *Type:* Real Claude Code subagent (`.claude/agents/geos-postprocess.md`,
  `model: sonnet`), dispatched via the Agent tool.
- *Tools:* postproc MCP tools (`read_vtk_output`, `extract_field`,
  `screenshot_field`, `compare_timesteps`, `compute_darcy_velocity`,
  `compute_material_balance`, `compute_well_performance`) + `sanity_check` +
  `Read`. No deck-editing tools — compute-and-return only.
- *Inputs:* absolute VTK path(s) + fields of interest; *Outputs:*
  `PostprocessResult` JSON (`src/agents4geos/dispatch/results.py`).
- *Coordination:* post-run compute-and-return — its driver is the **publication
  -quality figure contract** (Crameri colormaps, SI-unit titles, no rainbow/jet),
  not parallelism; it does not fan out.
```

- [ ] **Step 4: Add a coordination note to AGENTS.md §6**

In `AGENTS.md` §6, under the "### Fan-out" or a short new note after it, add:

```markdown
### Quality-contract subagent

A subagent can exist purely to make a quality standard non-skippable, even when it
never fans out. Its contract re-instantiates with fresh attention on every
dispatch, so a MUST actually holds — unlike inline guidance that degrades over a
long orchestrator session.

*Current example (2026-06-10):* `geos-postprocess` enforces the publication-quality
figure contract (Crameri scientific colormaps, SI-unit titles, rainbow/`jet`
banned) on every post-run analysis, backed in code by `parse_postprocess_result`.
```

- [ ] **Step 5: Commit**

```bash
git add skills/geos:run.md AGENTS.md
git commit -m "feat(orchestrator): dispatch geos-postprocess after run; register in AGENTS.md (tnt)"
```

---

### Task 7: Runbook entry + full-suite verification

**Files:**
- Modify: `tests/dispatch/RUNBOOK.md`

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest tests/ -q`
Expected: PASS — cw7 baseline was 203 passing; this adds the colormap (6),
screenshot guard (2), and PostprocessResult (6) tests. No regressions.

- [ ] **Step 2: Add the live-gate runbook entry**

Append to `tests/dispatch/RUNBOOK.md`:

```markdown
## geos-postprocess live gate (tnt)

**Goal:** dispatch `geos-postprocess` against a real GEOS VTK output in an
MCP-registered `/geos` session and confirm a contract-valid `PostprocessResult`.

**Steps:**
1. Run a small deck through `/geos:run`; locate the final-timestep `.vtu`.
2. From the orchestrator, dispatch `geos-postprocess` with the absolute VTK path.
3. Parse its JSON with `parse_postprocess_result` — must succeed.
4. Assert each figure's `colormap` is a `cmc.*` map (NOT jet/rainbow/coolwarm) and
   its `title` ends in a bracketed SI unit; assert each figure `path` exists.

**Status:** PENDING — record PASS once run live with the MCP server registered
(headless build sessions lack it; cw7 RUNBOOK pattern).
```

- [ ] **Step 3: Commit**

```bash
git add tests/dispatch/RUNBOOK.md
git commit -m "test(dispatch): geos-postprocess live-gate runbook entry — PENDING (tnt)"
```

---

## Self-Review notes (for the implementer)

- **Spec coverage:** §5.1 colormap science → Task 1 module + Task 4/5 contracts;
  §5.2 cmcrameri dep → Task 1; §5.3 screenshot_field default+guard → Task 2; §5.4
  agent contract → Task 4; §5.5 PostprocessResult → Task 3; §5.6 slash hardening →
  Task 5; §5.7 orchestrator wiring → Task 6; §5.8 AGENTS.md → Task 6; §6 testing →
  Tasks 1-3,7; §7 runbook → Task 7. `inspect`/`validate` declines are recorded in
  the spec §3, no code — correct (nothing to implement).
- **Type consistency:** `resolve_colormap`, `BANNED_COLORMAPS`, `SEQUENTIAL_DEFAULT`,
  `DIVERGING_DEFAULT`, `CYCLIC_DEFAULT` defined in Task 1 and reused verbatim in
  Tasks 2, 3, 4, 5. `PostprocessResult`/`FieldStat`/`FigureRef`/`MAP_TYPES` defined
  in Task 3 and matched by the JSON shape in Task 4 and tests.
- **Dependency direction:** `dispatch/results.py` imports `BANNED_COLORMAPS` from
  `tools/colormaps.py` — acceptable (results validate tool outputs against the tool
  layer's policy; no cycle, `colormaps.py` imports nothing from `dispatch`).
```
