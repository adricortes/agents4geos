"""Structured results returned by dispatched compute subagents (geos-mesh, geos-fluids).

This is the contract between the fan-out subagents and the orchestrator: each
subagent returns a JSON object that the orchestrator validates here before applying
it to the document. Mirrors src/agents4geos/review/findings.py (the reviewer seam).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agents4geos.tools.colormaps import BANNED_COLORMAPS

MESH_KINDS = ("internal", "vtk")
INTERNAL_MESH_KEYS = (
    "xCoords", "yCoords", "zCoords", "nx", "ny", "nz", "elementTypes",
)


@dataclass(frozen=True)
class ConstitutiveSpec:
    element_type: str
    name: str
    attributes: dict


@dataclass(frozen=True)
class FluidResult:
    model_type: str
    constitutive: list[ConstitutiveSpec]
    pvt_table_paths: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class MeshResult:
    mesh_kind: str
    internal_mesh: dict | None = None
    vtk_path: str | None = None
    stats: dict = field(default_factory=dict)
    notes: str = ""

    @property
    def is_internal(self) -> bool:
        return self.mesh_kind == "internal"

    @property
    def is_vtk(self) -> bool:
        return self.mesh_kind == "vtk"


def parse_fluid_result(d: dict) -> FluidResult:
    """Validate and parse a geos-fluids JSON result. Raises ValueError on bad shape."""
    missing = {"model_type", "constitutive"} - d.keys()
    if missing:
        raise ValueError(f"FluidResult missing keys: {sorted(missing)}")
    if not isinstance(d["constitutive"], list):
        raise ValueError("FluidResult 'constitutive' must be a list")
    specs: list[ConstitutiveSpec] = []
    for i, item in enumerate(d["constitutive"]):
        cmissing = {"element_type", "name", "attributes"} - item.keys()
        if cmissing:
            raise ValueError(f"constitutive[{i}] missing keys: {sorted(cmissing)}")
        bad = {k: type(v).__name__ for k, v in item["attributes"].items()
               if not isinstance(v, str)}
        if bad:
            raise ValueError(
                f"constitutive[{i}] attribute values must be GEOS literal strings "
                f"(e.g. '{{ gas, water }}'), got non-strings: {bad}"
            )
        specs.append(
            ConstitutiveSpec(item["element_type"], item["name"], item["attributes"])
        )
    return FluidResult(
        model_type=d["model_type"],
        constitutive=specs,
        pvt_table_paths=d.get("pvt_table_paths", []),
        notes=d.get("notes", ""),
    )


def parse_mesh_result(d: dict) -> MeshResult:
    """Validate and parse a geos-mesh JSON result. Raises ValueError on bad shape."""
    if "mesh_kind" not in d:
        raise ValueError("MeshResult missing key: 'mesh_kind'")
    kind = d["mesh_kind"]
    if kind not in MESH_KINDS:
        raise ValueError(f"invalid mesh_kind {kind!r}; expected one of {MESH_KINDS}")
    if kind == "internal":
        im = d.get("internal_mesh")
        if not isinstance(im, dict):
            raise ValueError("mesh_kind 'internal' requires an 'internal_mesh' dict")
        imissing = set(INTERNAL_MESH_KEYS) - im.keys()
        if imissing:
            raise ValueError(f"internal_mesh missing keys: {sorted(imissing)}")
    else:  # vtk
        if not d.get("vtk_path"):
            raise ValueError("mesh_kind 'vtk' requires a 'vtk_path'")
    return MeshResult(
        mesh_kind=kind,
        internal_mesh=d.get("internal_mesh"),
        vtk_path=d.get("vtk_path"),
        stats=d.get("stats", {}),
        notes=d.get("notes", ""),
    )


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
