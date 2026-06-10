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

# Matplotlib builtins used as fallbacks when cmcrameri is unavailable.
_CMC_FALLBACK = {
    SEQUENTIAL_DEFAULT: "viridis",
    DIVERGING_DEFAULT:  "RdBu_r",
    CYCLIC_DEFAULT:     "twilight",   # matplotlib's true cyclic map
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
        return _CMC_FALLBACK.get(name, "viridis")
    return name
