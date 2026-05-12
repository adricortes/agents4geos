# Black oil

> Per-category detail file for the `/geos` example catalog.
> See [`../example_catalog.md`](../example_catalog.md) for scope, format
> conventions, the top-level category router, and the benchmark
> cross-reference table.

Source directory: `compositionalMultiphaseWell/` — all 4 Black Oil decks live
here (none in compositional flow without wells, none in poromechanics). The
variants form a 2×2 grid: **saturated / unsaturated** (above / below bubble
point) × **Stone-I / Stone-II** (3-phase relperm interpolation model).

## Variant axes

- **Saturation state**: saturated (free gas phase, Rs = Rs_max) vs unsaturated
  (all gas dissolved, Rs < Rs_max).
- **3-phase relperm interpolation**: Stone-I (default, unsuffixed) vs Stone-II
  (suffix `_stone2`).
- All four variants share the **same mesh, well layout, and PVT table
  structure** — they differ only in initial composition and the relperm element.

## Decision rule (stage 2)

- Default to **saturated + Stone-I** for any plain "black oil" / "oil + gas +
  water" / "depletion drive" request — it's the default-default that GEOS itself
  ships as the unsuffixed example.
- Pick **unsaturated** when the user describes oil below bubble point
  (Rs < Rs_max, no free gas phase initially), undersaturated drainage, or
  pressure-maintained history matches.
- Pick **Stone-II** when the user mentions intermediate-wet relperm,
  asphalt-water systems, or specifically asks for "Stone 2" / "modified Stone".
- All four decks share skeleton — the orchestrator can clone the canonical entry
  and swap.

## Entries

### black_oil_wells_saturated_3d — saturated, Stone-I

**File:** `compositionalMultiphaseWell/black_oil_wells_saturated_3d.xml`
**One-liner:** Producer + water-injector pair in a 200×200×10 m oil reservoir
above bubble point with free gas, default Stone-I 3-phase relperm — the textbook
"black-oil waterflood" starter.
**Use as starter when:** the user asks for black-oil simulation, waterflood, oil
production with gas cap, or doesn't specify Stone-I vs Stone-II.

| Tag | Value |
|-----|-------|
| Physics | 3-component black oil (oil, gas, water), isothermal |
| Solver | `CompositionalMultiphaseReservoir` |
| Fluid | `BlackOilFluid` with PVT tables (Bo, Bg, Rs, viscosities); component order **oil, gas, water** |
| Relperm | Stone-I (default — `BrooksCoreyStone2RelativePermeability` is the explicit Stone-II equivalent) |
| Geometry | 3D box, 200 × 200 × 10 m, 4 × 4 × 2 = 32 cells (small; scale up for real cases) |
| Driving | One producer (BHP 12 MPa, target oil rate 0.05 m³/s), one injector (BHP 20 MPa, pure water stream `{0, 0, 1}`) |
| Wells | `InternalWell` defined inside `InternalMesh`, single perforation each, polyline geometry |
| Temperature | 297.15 K (24 °C) — surface-like, typical for shallow black-oil exemplars |
| Initial dt | 86 400 s (1 day) |
| Knowledge-module coverage | ✅ `BlackOilFluid` now wired in `fluid_models.py` (keyword: `"black oil"`, `"depletion drive"`, `"saturated oil"`) with proper {oil, gas, water} component order and PVTO/PVTG/PVTW table convention. ⚠️ Still missing from v0.1 README list (tracked in agents4geos-npm). Stone-I/II relperm not yet in a dedicated relperm-models module — Stone-II via `BrooksCoreyStone2RelativePermeability` element swap is documented in the dead-oil siblings list (separate follow-up). |
| Reuse | ★★★ — primary black-oil starter; the unsaturated and Stone-II siblings reuse this skeleton |

### Sibling variants (no separate entries)

- `black_oil_wells_saturated_3d_stone2.xml` — same as above with Stone-II relperm
- `black_oil_wells_unsaturated_3d.xml` — same skeleton, undersaturated initial composition
- `black_oil_wells_unsaturated_3d_stone2.xml` — combination of the two above
