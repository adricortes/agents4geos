# Reflexive subagent-conversion decisions + `geos-postprocess` quality contract

**Date:** 2026-06-10
**Issue:** `agents4geos-tnt` (epic `agents4geos-gy9`)
**Precedent:** cw7 per-tier routing fan-out pilot
(`docs/superpowers/specs/2026-06-09-per-tier-routing-fanout-pilot-design.md`)
**Status:** design approved (Adriano), pending spec review → implementation plan

---

## 1. The reframe — what "convert to a subagent" actually means

cw7 did **not** replace the `/geos:mesh` and `/geos:fluids` slash commands with
subagents. It **added a second form**: a `.claude/agents/*.md` subagent that the
orchestrator dispatches *internally* during a build (Stage C fan-out), while the
slash command remains the *interactive user surface*. AGENTS.md states this
explicitly: *"NOT user-invocable (the `/geos:mesh` slash command remains for
direct use)."*

So the question for `agents4geos-tnt` is **not** "should this slash command stop
existing?" It is:

> **Does the orchestrator's build/run pipeline benefit from dispatching this work
> as an isolated subagent?**

A slash command is an interactive surface; a subagent is an internal compute
primitive the orchestrator fans out or pipelines. Converting **grows a second
form**; it does not migrate the first. For every converted agent in this issue,
**both forms are kept** (cw7 pattern) — confirmed with Adriano.

## 2. The decision driver

cw7's driver hierarchy, in priority order:

> **correctness > capability > cost > context + parallelism**

A subagent form earns its keep only when one of these *fires* for the
orchestrator's use of that agent. Two refinements learned while writing this spec:

- **Interactive surfaces resist conversion.** A subagent returns structured JSON
  to the *orchestrator*, then discards its context. If the *user* is the one who
  wants the answer/visual (schema Q&A, an exploratory field screenshot), routing
  through a throwaway subagent context loses the thing the user came for.
  Compute-and-return wins only when nobody needs the intermediate conversation.
- **A subagent is a quality firewall, not only a parallelism tool.** Inline
  guidance inside a 19 KB orchestrator skill competes with everything else in a
  long session and degrades. A subagent re-instantiates its full contract on
  *every* dispatch with fresh attention — so a "MUST" actually holds. This is the
  **correctness** driver, and it can justify a subagent that never fans out.

## 3. Per-agent reflexive verdict

| Agent | Tier→Model | Driver that fires | Verdict |
|-------|-----------|-------------------|---------|
| **geos:relperm** | 2 → Sonnet | context+parallelism — stateless curve/table compute, identical shape to fluids/mesh; a natural **3rd Stage C fan-out sibling** for multiphase decks | **Convert** ✅ (follow-up) |
| **geos:postprocess** | 2 → Sonnet | **correctness** — enshrine the publication-quality figure contract as a hard, fresh-context MUST | **Convert** ✅ (this session) |
| **geos:schema** | 1 → Haiku | cost + context-hygiene — keep verbose schema dumps out of the orchestrator's Opus context; **proves Tier-1 Haiku routing** (a win cw7 never exercised) | **Convert (pilot)** ⚠️ (follow-up) |
| **geos:inspect** | 1 → Haiku | none — almost always a direct, terminal user request ("what's in this deck?"); no build-flow fan-out trigger | **Keep inline** ❌ |
| **geos:validate** | 2 → Sonnet | none (mostly) — its tools (`validate_xml`, `validate_cross_references`, `sanity_check`) **already run inline** in the Stage C/R pipeline, and the Opus `geos-reviewer` already owns the judgment layer | **Keep inline** ❌ |

### Decline rationale (recorded per the issue's "decide explicitly and note it")

- **geos:inspect** — inline by decision. It is an interactive, terminal user
  request with no orchestrator fan-out trigger. *Revisit only if* a future
  pipeline ingests an external deck and needs a structured digest before editing
  (speculative — YAGNI now).
- **geos:validate** — inline by decision. The validation *tools* are already
  one-line MCP calls inside the orchestrator's Stage C/R flow; wrapping them in a
  dispatched subagent adds round-trip + model overhead for work already cheap and
  deterministic. The *judgment* layer is already owned by the Tier-3 Opus
  `geos-reviewer`. *Revisit only if* Opus-review cost becomes a problem — then a
  cheap Sonnet `geos-validate` pre-screen (fix mechanical schema/xref errors
  before the expensive intent review) could pipeline *ahead* of the reviewer,
  reusing the `review/findings.py` contract shape.

## 4. Scope of this session

**`geos-postprocess` only**, done thoroughly. `relperm` and `schema` are
mechanical once the postprocess conversion re-confirms the cw7 recipe; they are
filed as follow-up issues (§9). This honors the issue's "one or two at a time"
guidance and matches Adriano's investment in getting the figure contract right.

## 5. `geos-postprocess` design

### 5.1 Colormap science (the substance Adriano asked for)

Publication-quality figures are not just *titled* — they use a **perceptually
uniform, color-blind-safe, grayscale-readable** colormap chosen **by data type**.
Sources: Fabio Crameri's Scientific Colour Maps
(<https://www.fabiocrameri.ch/colourmaps/>), the scientific-palette rationale
(<https://conceptviz.app/blog/scientific-color-palette-for-research-papers-and-posters>).

| Field data type | Default map | Rationale |
|-----------------|-------------|-----------|
| **Sequential** (saturation, porosity, concentration, pressure magnitude, density) | **`cmc.batlow`** | Crameri flagship; perceptually uniform, CVD-safe, grayscale-readable |
| **Diverging** (Δfields, signed Darcy velocity, anomalies about a center) | **`cmc.vik`** | scientific diverging; honest zero-crossing |
| **Cyclic** (phase/angle, rare) | **`cmc.romaO`** | cyclic-safe |
| **Banned** | `jet`, `rainbow`, `hsv`, **and `coolwarm` as a silent default** | non-uniform and/or not grayscale-robust |

> Note: `viridis` (matplotlib) is itself perceptually uniform and CVD-safe and is
> an acceptable sequential fallback; `coolwarm` is *not* in the scientific class
> and degrades in grayscale — its removal as the default is the core fix.

### 5.2 Colormap availability — `cmcrameri` dependency

Decided with Adriano (explicit override of the minimize-deps default): add the
maintained `cmcrameri` PyPI package. On `import cmcrameri.cm` it registers
`cmc.batlow`, `cmc.vik`, `cmc.romaO`, … with matplotlib's colormap registry.
`screenshot_field` passes `cmap=colormap` straight to PyVista's `add_mesh`, which
resolves the name via matplotlib — so `cmap="cmc.batlow"` "just works" once the
package is imported.

- Add `cmcrameri` to the appropriate dependency group in `pyproject.toml`.
- Import it where `screenshot_field` lives (or a small `postproc/colormaps.py`
  registration shim imported at tool-module load) so the `cmc.*` names are
  registered before any plot call.
- **Fallback:** if `cmcrameri` is unavailable at runtime, fall back to `viridis`
  (sequential) / a matplotlib diverging map, and emit a one-line warning rather
  than crashing — a missing colormap dep must never block a screenshot.

### 5.3 `screenshot_field` change

- The tool cannot reliably infer a field's data type, so its **static default
  becomes the safe scientific sequential map**: `colormap: str = "cmc.batlow"`
  (replacing `"coolwarm"`). The **caller decides** data type and passes `cmc.vik`
  for diverging fields — this decision is the *agent's* (and slash command's)
  contractual job, per §5.4/§5.6. The signature keeps the `colormap` override so
  an advanced user can still force any map.
- Reject `jet`/`rainbow`/`hsv` (and warn) at the tool boundary, steering to the
  scientific equivalent. (Implementation: a small validate-and-map helper.)
- Everything else (titled vertical colorbar, axis widget, figure title, white
  background, font sizes) is already publication-grade — keep it.

### 5.4 The contract — `.claude/agents/geos-postprocess.md`

- Frontmatter: `model: sonnet`; `tools:` = the 7 postproc MCP tools
  (`read_vtk_output`, `extract_field`, `screenshot_field`, `compare_timesteps`,
  `compute_darcy_velocity`, `compute_material_balance`, `compute_well_performance`)
  + `sanity_check` + `Read`. **No deck-editing tools** — compute-and-return.
- Body makes these **MUST**, not advice:
  1. Every figure carries a `title` ending in the **SI unit in brackets**
     (e.g. `"Pressure at t = 1 yr [Pa]"`).
  2. Colormap is chosen **by data type** from the §5.1 table; `jet`/rainbow/`hsv`
     and `coolwarm`-as-default are forbidden.
  3. Always `read_vtk_output` first to discover available fields/ranges.
  4. Return **structured JSON only** (no prose) — a `PostprocessResult`.

### 5.5 Result contract — `PostprocessResult` (new in `dispatch/results.py`)

Mirrors `MeshResult`/`FluidResult`. TDD: add the dataclass + a
`parse_postprocess_result(d)` validator that raises `ValueError` on bad shape.

```text
PostprocessResult:
  fields:   list[FieldStat]   # {name, min, max, mean, std, units}
  figures:  list[FigureRef]   # {path, title, units, colormap, map_type}
  derived:  dict              # material_balance / well_performance / darcy, optional
  notes:    str
```

Validator checks: `fields` is a list of dicts with the stat keys; each `figures`
entry has `path` + `title` + `colormap` + `map_type ∈ {sequential,diverging,cyclic}`;
**a figure whose `colormap` is a banned map fails validation** (the contract is
enforced in code at the seam, not only in the prompt).

### 5.6 Slash-command hardening — `skills/geos:postprocess.md`

Elevate the existing "ALWAYS provide a descriptive title" *advice* to a
**contract**, and add the §5.1 colormap-by-data-type rule + the banned list. The
slash command and the subagent now state the identical standard — two enforcement
points, one source of truth.

### 5.7 Orchestrator wiring — `skills/geos.md` (`geos:run` flow)

Where the run/post-run flow currently does ad-hoc inline screenshots, dispatch the
`geos-postprocess` subagent (Agent tool) and apply its `PostprocessResult`. Keep
an inline fallback: a subagent failure never blocks post-processing (cw7 rule).
Postprocessing belongs to the Tier-3 `geos:run` flow, not the creation flow.

### 5.8 AGENTS.md updates

- §3 registry: add a `geos-postprocess` real-subagent entry (model: sonnet,
  tools, inputs/outputs = `PostprocessResult`, coordination), and annotate the
  `geos:postprocess` entry that a dispatch form now exists.
- §6 coordination: note `geos-postprocess` under the run/post-run flow (a
  compute-and-return advisor, not a fan-out sibling — its driver is the quality
  contract).
- §2: optionally note the "subagent as quality firewall" rationale.

## 6. Testing (TDD)

1. `tests/dispatch/` — `parse_postprocess_result` happy path + each failure mode
   (missing stat keys, missing figure `path`, banned colormap, bad `map_type`).
2. Colormap registration test — after importing the shim, assert `cmc.batlow`
   and `cmc.vik` resolve via matplotlib; assert the fallback path when `cmcrameri`
   is monkeypatched absent.
3. `screenshot_field` — banned-map rejection/steering; default is no longer
   `coolwarm`.
4. Full suite green (`uv run pytest tests/`); cw7 baseline was 203 passing.

## 7. Live gate + runbook

Add a `tests/dispatch/RUNBOOK.md` entry: dispatch `geos-postprocess` against a real
VTK output in an MCP-registered `/geos` session; confirm a contract-valid
`PostprocessResult` with a `cmc.*` colormap and SI-unit title. If run headless
without the MCP server, record **PENDING** (cw7 RUNBOOK pattern), do not block.

## 8. Out of scope / explicitly declined

- `geos:inspect`, `geos:validate` — kept inline (§3 rationale).
- The ParaView-Colormap-Generator repo (hex→XML) — not used; `cmcrameri` +
  matplotlib registry is the cleaner path for the PyVista rendering stack.
- A `coolwarm` purge across the codebase beyond `screenshot_field`'s default —
  only the default and the contract change here.

## 9. Follow-up issues to file

1. **Convert `geos:relperm`** → `geos-relperm` subagent (3rd Stage C fan-out
   sibling) + `RelPermResult` dataclass. Mechanical; follows this recipe.
2. **Pilot `geos:schema`** → `geos-schema` subagent (`model: haiku`) for
   orchestrator-side verbose introspection; proves Tier-1 routing + context
   hygiene. Keep `/geos:schema` inline for interactive user Q&A.
