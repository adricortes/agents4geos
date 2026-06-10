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
