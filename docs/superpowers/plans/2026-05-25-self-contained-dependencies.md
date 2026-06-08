# Self-Contained Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make agents4geos install without sibling-repo clones by adopting the geos-tui schema/xml/domain engine as first-class code and externalizing pyvista (PyPI) and pyResToolbox-SI (git pin).

**Architecture:** Move 14 library files from geos-tui into `src/agents4geos/geos/{schema,xml,domain}/`, rewrite all `geos_tui.*` imports to `agents4geos.geos.*`, then drop the three editable path sources from `pyproject.toml`. Removes `geos-tui` and `textual` deps with zero new deps added.

**Tech Stack:** Python 3.11+, uv, lxml, pytest. Spec: `docs/superpowers/specs/2026-05-25-self-contained-dependencies-design.md`.

---

### Task 1: Branch and capture baseline

**Files:** none (git + verification only)

- [ ] **Step 1: Create the working branch**

```bash
cd /home/adriano/codes/agents4geos
git checkout -b self-contained-deps
```

- [ ] **Step 2: Capture baseline test state (must be green before refactor)**

Run: `uv run pytest tests/ -q`
Expected: all tests PASS (this is the editable-geos_tui baseline). Record the pass count; it must match after the refactor.

- [ ] **Step 3: Capture baseline schema element count**

Run: `uv run python -c "from agents4geos.config import get_schema; print(len(get_schema().elements))"`
Expected: `259`

---

### Task 2: Adopt the geos-tui engine files

Copy the 14 on-disk working-tree files (NOT `git archive` — `domain/scope.py` is untracked in geos-tui) into a new owned package.

**Files:**
- Create: `src/agents4geos/geos/__init__.py`
- Create: `src/agents4geos/geos/{schema,xml,domain}/` (14 files copied)
- Create: `src/agents4geos/geos/ORIGIN.md`

- [ ] **Step 1: Copy the three subpackages from the geos-tui working tree**

```bash
cd /home/adriano/codes/agents4geos
mkdir -p src/agents4geos/geos
cp -r /home/adriano/geos-tui/src/geos_tui/schema src/agents4geos/geos/schema
cp -r /home/adriano/geos-tui/src/geos_tui/xml    src/agents4geos/geos/xml
cp -r /home/adriano/geos-tui/src/geos_tui/domain src/agents4geos/geos/domain
touch src/agents4geos/geos/__init__.py
# Drop any copied cache dirs that came along
rm -rf src/agents4geos/geos/schema/.cache
```

- [ ] **Step 2: Verify exactly the expected files landed**

Run: `find src/agents4geos/geos -name '*.py' | sort`
Expected: 15 files — `geos/__init__.py` plus schema/(4), xml/(4), domain/(6).

- [ ] **Step 3: Write the provenance note**

Create `src/agents4geos/geos/ORIGIN.md`:

```markdown
# Origin of agents4geos/geos

This package is the schema/XML/domain engine **adopted from geos-tui** and now
owned by agents4geos. geos-tui (a Textual TUI for GEOS) is **superseded** by
agents4geos's natural-language interface and is no longer developed.

| Field | Value |
|-------|-------|
| Adopted from | geos-tui working tree at commit `b8f95258` |
| Note | `domain/scope.py` was untracked in geos-tui; the on-disk version was taken |
| Adopted on | 2026-05-25 |

This is owned code, not a tracked vendor snapshot — edit it freely here. There
is no upstream to sync against.
```

- [ ] **Step 4: Commit the raw adoption (imports still broken — that's expected)**

```bash
git add src/agents4geos/geos/
git commit -q -m "feat(geos): adopt geos-tui schema/xml/domain engine (pre-rewrite)"
```

---

### Task 3: Rewrite all imports `geos_tui.* -> agents4geos.geos.*`

**Files:**
- Modify: all of `src/agents4geos/geos/**/*.py` (9 internal import lines)
- Modify: `src/agents4geos/config.py`, `src/agents4geos/state/documents.py`, `src/agents4geos/tools/preproc_tools.py`, `src/agents4geos/tools/schema_tools.py`, `src/agents4geos/tools/xml_tools.py`
- Modify: `tests/conftest.py`, `tests/test_state.py`

- [ ] **Step 1: Rewrite internal imports in the adopted files**

```bash
grep -rl 'geos_tui\.' src/agents4geos/geos/ | xargs sed -i 's/geos_tui\./agents4geos.geos./g'
```

- [ ] **Step 2: Rewrite consumer imports in source and tests**

```bash
grep -rl 'geos_tui' src/agents4geos/config.py src/agents4geos/state/ src/agents4geos/tools/ tests/ | xargs sed -i 's/geos_tui\./agents4geos.geos./g'
```

- [ ] **Step 3: Verify NO `geos_tui` reference remains anywhere in the repo**

Run: `grep -rn 'geos_tui' src/ tests/`
Expected: no output (exit 1). If anything prints, fix it by hand.

- [ ] **Step 4: Verify imports resolve and schema still loads from the adopted engine**

Run: `uv run python -c "from agents4geos.config import get_schema; print(len(get_schema().elements))"`
Expected: `259` (note: the venv still has editable geos-tui installed, but nothing imports it now).

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest tests/ -q`
Expected: same pass count as Task 1 Step 2.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -q -m "refactor(geos): rewrite geos_tui imports to agents4geos.geos"
```

---

### Task 4: Externalize deps in pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit `[project].dependencies` — remove `geos-tui`**

Replace the `dependencies` list with:

```toml
dependencies = [
    "fastmcp>=2.0",
    "lxml>=5.0",
    "pyvista>=0.43",
    "numpy>=1.24",
]
```

- [ ] **Step 2: Replace `[tool.uv.sources]` — drop geos-tui and pyvista paths, git-pin pyResToolbox**

Replace the entire `[tool.uv.sources]` block with:

```toml
[tool.uv.sources]
pyrestoolbox = { git = "https://github.com/adricortes/pyResToolbox.git", rev = "bad0208" }
```

Note: `pyvista` now resolves from PyPI (no source override). `geos-tui` is gone entirely.

- [ ] **Step 3: Verify the file has no remaining path sources**

Run: `grep -n 'path =\|geos-tui\|editable' pyproject.toml`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -q -m "build: externalize pyvista (PyPI) and pyResToolbox (git pin); drop geos-tui"
```

---

### Task 5: Re-sync and verify the new dependency graph

**Files:**
- Modify: `uv.lock` (regenerated)

- [ ] **Step 1: Re-sync from the new pyproject**

Run: `uv sync --all-extras`
Expected: resolves with no `file://` path sources. pyvista resolves from PyPI; pyrestoolbox clones from git at `bad0208`.

> If the git clone fails to authenticate (pyResToolbox is private until issue
> `agents4geos-d1a` makes it public), either make the repo public first, or for
> LOCAL verification only temporarily use
> `{ git = "git+ssh://git@github.com/adricortes/pyResToolbox.git", rev = "bad0208" }`.
> The shipped pyproject must keep the https URL so evaluators can clone once it
> is public. Revert any ssh edit before the final commit.

- [ ] **Step 2: Confirm geos-tui and textual are gone from the environment**

Run: `uv pip list | grep -iE 'geos-tui|textual' || echo "GONE — neither installed"`
Expected: `GONE — neither installed`

- [ ] **Step 3: Verify schema loads and tests pass against the synced env**

Run: `uv run python -c "from agents4geos.config import get_schema; print(len(get_schema().elements))"`
Expected: `259`

Run: `uv run pytest tests/ -q`
Expected: same pass count as Task 1.

- [ ] **Step 4: Commit the lockfile**

```bash
git add uv.lock
git commit -q -m "build: regenerate uv.lock without path sources"
```

---

### Task 6: Fresh-clone smoke test (no sibling repos)

This reproduces the evaluator path that caught the textual bug last time.

**Files:** none (throwaway `/tmp` checkout)

- [ ] **Step 1: Push the branch so it can be cloned**

```bash
git push -u origin self-contained-deps
```

- [ ] **Step 2: Clone ONLY agents4geos into a scratch dir and sync**

```bash
SCRATCH=/tmp/a4g-selfcontained-test && rm -rf "$SCRATCH" && mkdir -p "$SCRATCH" && cd "$SCRATCH"
git clone --depth 1 -b self-contained-deps git@github.com:adricortes/agents4geos.git
cd agents4geos
uv sync --all-extras
```

Expected: sync succeeds with NO sibling `geos-tui`/`pyResToolbox`/`pyvista` directories present.

- [ ] **Step 3: Verify the bundled schema works in the clean clone**

```bash
cd /tmp/a4g-selfcontained-test/agents4geos
uv run python -c "from agents4geos.config import get_schema; print('OK', len(get_schema().elements))"
```

Expected: `OK 259`

- [ ] **Step 4: Clean up the scratch dir**

```bash
rm -rf /tmp/a4g-selfcontained-test
```

---

### Task 7: Remove the band-aid and simplify the README

**Files:**
- Delete: `scripts/install-for-evaluators.sh`
- Modify: `README.md` (Quick Start + Editable Dependencies sections)

- [ ] **Step 1: Delete the evaluator bootstrap script**

```bash
git rm scripts/install-for-evaluators.sh
```

- [ ] **Step 2: Replace the README "Quick Start for Evaluators" section**

In `README.md`, replace the body of the "Quick Start for Evaluators" section with:

```markdown
## Quick Start for Evaluators

```bash
git clone https://github.com/adricortes/agents4geos.git
cd agents4geos
uv sync --all-extras
```

That's it — no GEOS build and no sibling repositories are required. The parsed
GEOS schema is bundled (`src/agents4geos/.cache/schema.json`), and the
schema/XML engine lives in this repo (`src/agents4geos/geos/`). The `fluids`
extra pulls `pyResToolbox` (SI fork) from git automatically. Users who later
build GEOS can set `GEOS_SCHEMA` to override the bundled schema.

Then register the MCP server — see [Installation → Step 3](#3-set-up-a-workspace).
```

- [ ] **Step 3: Update the "Editable Dependencies" table**

In `README.md`, replace the "Editable Dependencies" subsection (the table of
three repos that "must be available locally") with:

```markdown
### Dependencies

| Dependency | Source | What it provides |
|------------|--------|------------------|
| `agents4geos.geos` (in-repo) | this repo, `src/agents4geos/geos/` | Schema parser, XML reader/writer, templates, validation (adopted from the superseded geos-tui) |
| [pyResToolbox](https://github.com/adricortes/pyResToolbox) (SI fork) | git pin (`fluids` extra) | Fluid PVT, relative permeability, well performance |
| [PyVista](https://github.com/pyvista/pyvista) | PyPI `pyvista>=0.43` | Mesh creation, VTK I/O, headless visualization |
```

- [ ] **Step 4: Verify no stale references to the deleted script or old layout**

Run: `grep -rn 'install-for-evaluators\|../../geos-tui\|../pyResToolbox' README.md`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -q -m "docs: drop install band-aid; README reflects self-contained install"
```

---

### Task 8: Beads bookkeeping and push

**Files:** none (beads + git)

- [ ] **Step 1: File the adoption issue and close superseded ones**

```bash
ADOPT=$(bd create --title="Adopt geos-tui schema/xml/domain engine into agents4geos" \
  --description="Moved geos_tui.{schema,xml,domain} (14 files) into src/agents4geos/geos/ as owned code; removed geos-tui + textual deps. geos-tui is superseded by agents4geos. See docs/superpowers/specs/2026-05-25-self-contained-dependencies-design.md." \
  --type=task --priority=0 | grep -oE 'agents4geos-[a-z0-9]+' | head -1)
echo "adoption issue: $ADOPT"
bd close "$ADOPT" --reason="Implemented on branch self-contained-deps"
bd close agents4geos-cc4 --reason="Superseded: geos-tui adopted into src/agents4geos/geos/ instead of pinned"
bd close agents4geos-dms --reason="Superseded: agents4geos no longer depends on geos-tui, so its textual override is irrelevant here"
bd close agents4geos-eqn --reason="pyvista switched to PyPI pyvista>=0.43"
bd close agents4geos-nsu --reason="pyResToolbox-SI git-pinned in pyproject"
```

- [ ] **Step 2: Narrow the visibility issue to what still needs access**

```bash
bd update agents4geos-d1a --title="Make agents4geos + pyResToolbox-SI public (or grant evaluator access)" \
  --notes="geos-tui no longer needs to be accessible — it was adopted into agents4geos. Only agents4geos itself and the git-pinned pyResToolbox-SI must be reachable by evaluators."
```

- [ ] **Step 3: Open a PR for the branch**

```bash
git push
gh pr create --title "Self-contained dependencies" --body "Adopts the geos-tui schema/xml/domain engine into src/agents4geos/geos/, externalizes pyvista (PyPI) and pyResToolbox-SI (git pin), and removes the install band-aid. Removes geos-tui + textual deps with zero new deps. Spec + plan under docs/superpowers/. Verified by fresh-clone smoke test (Task 6)."
```

- [ ] **Step 4: Push beads state**

```bash
bd dolt push
```

---

## Notes for the executor

- The venv keeps an editable geos-tui install until Task 5's `uv sync` rebuilds
  it. That's fine — after Task 3 nothing imports `geos_tui`, so the source of
  truth is already `src/agents4geos/geos/`.
- If `uv run pytest` needs a schema and none is set, it uses the committed
  `src/agents4geos/.cache/schema.json` — do not delete that cache.
- Keep the https git URL for pyResToolbox in the committed pyproject; ssh is for
  local-only verification when the repo is still private.
