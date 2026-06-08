# Self-Contained Dependencies — Design

**Date:** 2026-05-25
**Status:** Approved (pending spec review)
**Beads epic:** `agents4geos-lh7`

## Problem

agents4geos cannot be installed by a stranger without replicating Adriano's
`~/codes/` machine layout. `pyproject.toml` declares three editable *path*
dependencies:

```toml
[tool.uv.sources]
pyrestoolbox = { path = "../pyResToolbox", editable = true }
pyvista      = { path = "../pyvista", editable = true }
geos-tui     = { path = "../../geos-tui", editable = true }
```

`uv sync` therefore fails unless `geos-tui`, `pyResToolbox`, and `pyvista` are
cloned to exact sibling paths. geos-tui additionally drags in `textual` via its
own editable override, which surfaced as a transitive install failure during the
2026-05-22 company evaluation. The current mitigation
(`scripts/install-for-evaluators.sh` + bundled schema) is a band-aid.

## Goals

1. **Self-contained install** — core agents4geos installs from PyPI with no git
   clone, no sibling repos, no auth.
2. **Minimize dependencies** — remove deps that are not genuinely needed.

## Decisions (with rationale)

### geos-tui → adopt into agents4geos as first-class code

agents4geos uses geos-tui purely as a **library** — three subpackages,
`schema/`, `xml/`, `domain/` — and never touches `geos_tui.ui` or
`geos_tui.app` (the TUI). Those TUI parts are the *only* thing that pulls in
`textual`.

**geos-tui is superseded by agents4geos** (natural-language interface replaces
the TUI); Adriano will not develop geos-tui further. Therefore the engine is
**adopted as owned agents4geos code**, not vendored as a tracked snapshot. There
is no upstream to drift from — reinforced by the fact that `domain/scope.py` was
never even committed to geos-tui.

- **Move** the on-disk working-tree files (14 files, ~1.2k LOC) into
  `src/agents4geos/geos/{schema,xml,domain}/`.
- **Rewrite** every internal import `geos_tui.X → agents4geos.geos.X` and the
  14 consumer import lines across 5 source + 2 test files.
- **Keep** the `xml/` subpackage name (namespaced as `agents4geos.geos.xml`;
  Python-3 absolute imports mean it does not shadow stdlib `xml`, and the code
  uses `lxml`, not stdlib `xml`).
- **Record** provenance in `src/agents4geos/geos/ORIGIN.md`: adopted from
  geos-tui working tree at commit `b8f95258` plus untracked `domain/scope.py`;
  note geos-tui is superseded.
- **Net dependency effect:** removes `geos-tui` *and* `textual`; adds **zero**
  new third-party deps (the subset needs only `lxml`, already present).

### pyvista → external, PyPI

The local editable pyvista checkout is confirmed **unmodified upstream**. Drop
the editable source; keep `pyvista>=0.43` resolved from PyPI. Remains a core
dependency for now (making it an optional extra is a follow-up — see Out of
Scope).

### pyResToolbox-SI → external, git-pinned

Stays Adriano's external repo (the SI-unit fork). Pin in `[tool.uv.sources]`:

```toml
pyrestoolbox = { git = "https://github.com/adricortes/pyResToolbox.git", rev = "<tag-or-commit>" }
```

under the `fluids` optional extra. Pin candidate: `bad0208`
(`3.0.5-16-gbad0208`) — a clean release tag is preferable if one is cut.

## Adoption set (14 files)

```
schema/  __init__.py  cache.py  model.py  parser.py
xml/     __init__.py  reader.py state.py  writer.py
domain/  __init__.py  curation.py  descriptions.py  scope.py  templates.py  wizard.py
```

`domain/scope.py` is untracked in geos-tui — take the on-disk version.
`domain/wizard.py` is not directly imported by agents4geos but is adopted whole
to preserve `domain/__init__.py` internal imports; confirm it adds no new deps.

## Rewrite surface (7 files, 14 import lines)

Source: `config.py`, `state/documents.py`, `tools/preproc_tools.py`,
`tools/schema_tools.py`, `tools/xml_tools.py`.
Tests: `conftest.py`, `test_state.py`.

## Resulting pyproject.toml

```toml
dependencies = ["fastmcp>=2.0", "lxml>=5.0", "pyvista>=0.43", "numpy>=1.24"]

[project.optional-dependencies]
fluids = ["pyrestoolbox>=3.1", "scipy>=1.10", "pandas>=2.0"]
dev    = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.uv.sources]
pyrestoolbox = { git = "https://github.com/adricortes/pyResToolbox.git", rev = "<pin>" }
```

No more `[tool.uv.sources]` path entries. Core install is PyPI-clean; only the
`fluids` extra needs git.

## Verification

1. `uv sync --all-extras` resolves with no path sources.
2. `uv run python -c "from agents4geos.config import get_schema; print(len(get_schema().elements))"`
   prints `259`.
3. Full `uv run pytest tests/` passes.
4. Fresh-clone smoke test in `/tmp` (same method that caught the textual bug):
   clone agents4geos alone, `uv sync --all-extras`, confirm no sibling repos
   needed.

## Beads bookkeeping

- `cc4` (pin geos-tui), `dms` (geos-tui textual override) → **close as
  superseded** by adoption.
- `eqn` (pyvista → PyPI), `nsu` (pyResToolbox git pin) → **done** by this work.
- `d1a` (repo visibility) → narrow to pyResToolbox-SI + agents4geos only;
  geos-tui no longer needs to be accessible.
- Delete `scripts/install-for-evaluators.sh`; simplify README Quick Start to a
  plain `uv sync`.
- New issue: "Adopt geos-tui schema/xml/domain engine into agents4geos".

## Out of scope (follow-ups)

- Make `pyvista` an optional `viz`/`mesh` extra (further minimization; changes
  tool availability when absent).
- Publish pyResToolbox-SI to PyPI (would make even the `fluids` extra
  PyPI-clean, removing the last git dependency).
