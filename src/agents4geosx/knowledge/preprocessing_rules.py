"""GEOS XML preprocessing pipeline and conventions.

Encodes the strict order of operations and syntax rules for XML
preprocessing features: file inclusion, parameter substitution,
unit conversion, and symbolic math evaluation.

Sourced from geos-xml-tools (GEOS-DEV/geosPythonPackages):
https://github.com/GEOS-DEV/geosPythonPackages/tree/main/geos-xml-tools/src/geos/xml_tools
"""

from __future__ import annotations

PROCESSING_PIPELINE: list[dict] = [
    {
        "stage": 1,
        "name": "include_merging",
        "description": "Merge <Included> file blocks into main document",
        "nesting_limit": 100,
    },
    {
        "stage": 2,
        "name": "parameter_substitution",
        "description": "Expand $Name$ patterns from <Parameters> section",
        "nesting_limit": 100,
    },
    {
        "stage": 3,
        "name": "unit_conversion",
        "description": "Evaluate [unit] bracket notation to SI values",
        "nesting_limit": None,
    },
    {
        "stage": 4,
        "name": "symbolic_math",
        "description": "Evaluate `expression` backtick notation",
        "nesting_limit": 100,
    },
    {
        "stage": 5,
        "name": "special_char_validation",
        "description": "Flag leftover $, [, ], ` as unresolved",
        "nesting_limit": None,
    },
]

PARAMETER_RULES: dict = {
    "regex": r"\$:?([a-zA-Z_0-9]*)\$?",
    "valid_name_chars": "[a-zA-Z_0-9]",
    "colon_prefix_optional": True,
    "trailing_dollar_optional": True,
    "max_nesting": 100,
    "source_element": "Parameters/Parameter",
    "source_attrs": {"name": "parameter name", "value": "parameter value"},
    "cli_override": True,
}

SYMBOLIC_MATH_RULES: dict = {
    "regex": r"\`([-+.*/() 0-9eE]*)\`",
    "allowed_chars": "+-.*/()" + "0123456789" + "eE ",
    "max_nesting": 100,
    "protected_elements": [
        {"element": "SymbolicFunction", "attribute": "expression"},
        {"element": "CompositeFunction", "attribute": "expression"},
    ],
}

INCLUDE_RULES: dict = {
    "max_depth": 100,
    "merge_strategy": "attributes overridden, named elements matched by name attr",
    "insert_only_elements": ["Nodeset"],
    "root_element": "Problem",
    "source_structure": "Included/File[@name]",
}

SPECIAL_CHARACTERS: list[str] = ["$", "[", "]", "`"]
