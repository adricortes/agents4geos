"""Tests for preprocessing rules knowledge module."""
import re
import pytest
from agents4geos.knowledge.preprocessing_rules import (
    PROCESSING_PIPELINE,
    PARAMETER_RULES,
    SYMBOLIC_MATH_RULES,
    INCLUDE_RULES,
    SPECIAL_CHARACTERS,
)


class TestProcessingPipeline:
    def test_has_five_stages(self):
        assert len(PROCESSING_PIPELINE) == 5

    def test_stages_ordered(self):
        stages = [s["stage"] for s in PROCESSING_PIPELINE]
        assert stages == [1, 2, 3, 4, 5]

    def test_includes_before_parameters(self):
        names = [s["name"] for s in PROCESSING_PIPELINE]
        assert names.index("include_merging") < names.index("parameter_substitution")

    def test_parameters_before_units(self):
        names = [s["name"] for s in PROCESSING_PIPELINE]
        assert names.index("parameter_substitution") < names.index("unit_conversion")

    def test_units_before_symbolic(self):
        names = [s["name"] for s in PROCESSING_PIPELINE]
        assert names.index("unit_conversion") < names.index("symbolic_math")

    def test_validation_is_last(self):
        assert PROCESSING_PIPELINE[-1]["name"] == "special_char_validation"


class TestParameterRules:
    def test_regex_matches_dollar_name_dollar(self):
        m = re.search(PARAMETER_RULES["regex"], "$myParam$")
        assert m is not None
        assert m.group(1) == "myParam"

    def test_regex_matches_dollar_colon_name(self):
        m = re.search(PARAMETER_RULES["regex"], "$:myParam")
        assert m is not None
        assert m.group(1) == "myParam"

    def test_regex_matches_dollar_name_no_trailing(self):
        m = re.search(PARAMETER_RULES["regex"], "$myParam")
        assert m is not None
        assert m.group(1) == "myParam"

    def test_max_nesting(self):
        assert PARAMETER_RULES["max_nesting"] == 100

    def test_source_element(self):
        assert PARAMETER_RULES["source_element"] == "Parameters/Parameter"


class TestSymbolicMathRules:
    def test_regex_matches_backtick_expr(self):
        m = re.search(SYMBOLIC_MATH_RULES["regex"], "`1 + 2.34e5*2`")
        assert m is not None
        assert m.group(1) == "1 + 2.34e5*2"

    def test_max_nesting(self):
        assert SYMBOLIC_MATH_RULES["max_nesting"] == 100

    def test_protected_elements(self):
        elements = [p["element"] for p in SYMBOLIC_MATH_RULES["protected_elements"]]
        assert "SymbolicFunction" in elements
        assert "CompositeFunction" in elements

    def test_regex_no_match_without_backticks(self):
        m = re.search(SYMBOLIC_MATH_RULES["regex"], "1 + 2")
        assert m is None


class TestIncludeRules:
    def test_max_depth(self):
        assert INCLUDE_RULES["max_depth"] == 100

    def test_insert_only_elements(self):
        assert "Nodeset" in INCLUDE_RULES["insert_only_elements"]

    def test_root_element(self):
        assert INCLUDE_RULES["root_element"] == "Problem"


class TestSpecialCharacters:
    def test_all_four_present(self):
        assert "$" in SPECIAL_CHARACTERS
        assert "[" in SPECIAL_CHARACTERS
        assert "]" in SPECIAL_CHARACTERS
        assert "`" in SPECIAL_CHARACTERS

    def test_length(self):
        assert len(SPECIAL_CHARACTERS) == 4
