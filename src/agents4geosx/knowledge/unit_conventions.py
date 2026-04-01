"""GEOS unit system conventions and pyResToolbox conversion bridge.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools

pyResToolbox unit mappings from the SI-refactored fork.
"""

from __future__ import annotations

import re

SI_PREFIXES: dict[str, dict] = {
    "giga":  {"value": 1e9,  "alt": "G"},
    "mega":  {"value": 1e6,  "alt": "M"},
    "kilo":  {"value": 1e3,  "alt": "k"},
    "hecto": {"value": 1e2,  "alt": "H"},
    "deca":  {"value": 1e1,  "alt": "D"},
    "":      {"value": 1.0,  "alt": ""},
    "deci":  {"value": 1e-1, "alt": "d"},
    "centi": {"value": 1e-2, "alt": "c"},
    "milli": {"value": 1e-3, "alt": "m"},
    "micro": {"value": 1e-6, "alt": "mu"},
    "nano":  {"value": 1e-9, "alt": "n"},
}

UNIT_DEFINITIONS: dict[str, dict] = {
    # SI base
    "gram":    {"value": 1e-3,               "alt": ["g", "grams"],          "usePrefix": True},
    "meter":   {"value": 1.0,                "alt": ["m", "meters"],         "usePrefix": True},
    "second":  {"value": 1.0,                "alt": ["s", "seconds"],        "usePrefix": True},
    "minute":  {"value": 60.0,               "alt": ["min", "minutes"],      "usePrefix": True},
    "hour":    {"value": 3600.0,             "alt": ["hr", "hours", "hrs"],  "usePrefix": True},
    "day":     {"value": 86400.0,            "alt": ["d", "dy"],             "usePrefix": True},
    "year":    {"value": 31557600.0,         "alt": ["yr", "years"],         "usePrefix": True},
    "pascal":  {"value": 1.0,                "alt": ["Pa"],                  "usePrefix": True},
    "newton":  {"value": 1.0,                "alt": ["N"],                   "usePrefix": True},
    "joule":   {"value": 1.0,                "alt": ["J"],                   "usePrefix": True},
    "watt":    {"value": 1.0,                "alt": ["W"],                   "usePrefix": True},
    # Imperial
    "pound":      {"value": 0.453592,           "alt": ["lb", "pounds", "lbs"],  "usePrefix": True},
    "poundforce": {"value": 0.453592 * 9.81,    "alt": ["lbf"],                  "usePrefix": True},
    "stone":      {"value": 6.35029,            "alt": ["st"],                   "usePrefix": True},
    "ton":        {"value": 907.185,            "alt": ["tons"],                 "usePrefix": True},
    "inch":       {"value": 0.0254,             "alt": ["in", "inches"],         "usePrefix": False},
    "foot":       {"value": 0.3048,             "alt": ["ft", "feet"],           "usePrefix": True},
    "yard":       {"value": 0.9144,             "alt": ["yd", "yards"],          "usePrefix": True},
    "rod":        {"value": 5.0292,             "alt": ["rd", "rods"],           "usePrefix": True},
    "mile":       {"value": 1609.34,            "alt": ["mi", "miles"],          "usePrefix": True},
    "acre":       {"value": 4046.86,            "alt": ["acres"],                "usePrefix": True},
    "gallon":     {"value": 0.00378541,         "alt": ["gal", "gallons"],       "usePrefix": True},
    "psi":        {"value": 6894.76,            "alt": [],                       "usePrefix": True},
    "psf":        {"value": 1853.184,           "alt": [],                       "usePrefix": True},
    # Other
    "dyne":       {"value": 1.0e-5,             "alt": ["dynes"],                "usePrefix": True},
    "bar":        {"value": 1.0e5,              "alt": ["bars"],                 "usePrefix": True},
    "atmosphere": {"value": 101325.0,           "alt": ["atm", "atmospheres"],   "usePrefix": True},
    "poise":      {"value": 0.1,                "alt": ["P"],                    "usePrefix": True},
    "barrel":     {"value": 0.1589873,          "alt": ["bbl", "barrels"],       "usePrefix": True},
    "horsepower": {"value": 745.7,              "alt": ["hp", "horsepowers"],    "usePrefix": True},
}

BRACKET_NOTATION_REGEX = r"([0-9]*?\.?[0-9]+(?:[eE][-+]?[0-9]*?)?)\ *?\[([-+.*/()a-zA-Z0-9]*)\]"

_UNIT_NAME_REGEX = r"[a-zA-Z]+"

PYRESTOOLBOX_MAPPING: dict[str, str] = {
    "mD": "MD_TO_M2",
    "psi": "PSI_TO_PA",
    "bar": "BAR_TO_PA",
    "atm": "ATM_TO_PA",
    "ft": "FT_TO_M",
    "in": "IN_TO_M",
    "bbl": "BBL_TO_M3",
    "gal": "GAL_TO_M3",
    "cP": "CP_TO_PAS",
    "lb/ft**3": "LBCUFT_TO_KGM3",
    "degF": "degf_to_degc",
    "degC": "degc_to_kelvin",
}


def _build_valid_unit_names() -> set[str]:
    """Build the complete set of valid unit names (full names + aliases + prefixed)."""
    names: set[str] = set()
    for name, defn in UNIT_DEFINITIONS.items():
        names.add(name)
        names.update(defn["alt"])
        if defn["usePrefix"]:
            for prefix_name, prefix_def in SI_PREFIXES.items():
                if prefix_name:
                    names.add(prefix_name + name)
                    names.add(prefix_def["alt"] + name)
                    for alt in defn["alt"]:
                        names.add(prefix_name + alt)
                        names.add(prefix_def["alt"] + alt)
    return names


_VALID_UNIT_NAMES = _build_valid_unit_names()


def validate_unit_expression(expr: str) -> dict:
    """Validate that a string's bracket unit expressions use valid GEOS units."""
    match = re.search(BRACKET_NOTATION_REGEX, expr)
    if match is None:
        return {"valid": True, "units_found": [], "unknown": []}
    unit_expr = match.group(2)
    unit_names = re.findall(_UNIT_NAME_REGEX, unit_expr)
    unknown = [u for u in unit_names if u not in _VALID_UNIT_NAMES]
    return {
        "valid": len(unknown) == 0,
        "units_found": unit_names,
        "unknown": unknown,
    }
