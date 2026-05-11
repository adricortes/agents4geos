"""Tests for unit conventions knowledge module."""
import re
import pytest
from agents4geos.knowledge.unit_conventions import (
    UNIT_DEFINITIONS,
    SI_PREFIXES,
    PYRESTOOLBOX_MAPPING,
    BRACKET_NOTATION_REGEX,
    validate_unit_expression,
)


class TestUnitDefinitions:
    def test_si_base_units_present(self):
        for unit in ["gram", "meter", "second", "pascal", "newton", "joule", "watt"]:
            assert unit in UNIT_DEFINITIONS, f"Missing SI base unit: {unit}"

    def test_imperial_units_present(self):
        for unit in ["pound", "foot", "psi", "barrel", "gallon"]:
            assert unit in UNIT_DEFINITIONS, f"Missing imperial unit: {unit}"

    def test_other_units_present(self):
        for unit in ["bar", "atmosphere", "poise", "dyne"]:
            assert unit in UNIT_DEFINITIONS, f"Missing other unit: {unit}"

    def test_unit_structure(self):
        for name, defn in UNIT_DEFINITIONS.items():
            assert "value" in defn, f"{name} missing 'value'"
            assert "alt" in defn, f"{name} missing 'alt'"
            assert "usePrefix" in defn, f"{name} missing 'usePrefix'"
            assert isinstance(defn["value"], (int, float)), f"{name} value not numeric"
            assert isinstance(defn["alt"], list), f"{name} alt not list"
            assert isinstance(defn["usePrefix"], bool), f"{name} usePrefix not bool"

    def test_meter_value_is_one(self):
        assert UNIT_DEFINITIONS["meter"]["value"] == 1.0

    def test_gram_value_is_1e_minus_3(self):
        assert UNIT_DEFINITIONS["gram"]["value"] == 1e-3

    def test_inch_no_prefix(self):
        assert UNIT_DEFINITIONS["inch"]["usePrefix"] is False


class TestSIPrefixes:
    def test_all_prefixes_present(self):
        expected = ["giga", "mega", "kilo", "hecto", "deca", "",
                    "deci", "centi", "milli", "micro", "nano"]
        for prefix in expected:
            assert prefix in SI_PREFIXES, f"Missing prefix: {prefix!r}"

    def test_kilo_value(self):
        assert SI_PREFIXES["kilo"]["value"] == 1e3

    def test_milli_value(self):
        assert SI_PREFIXES["milli"]["value"] == 1e-3

    def test_prefix_structure(self):
        for name, defn in SI_PREFIXES.items():
            assert "value" in defn
            assert "alt" in defn


class TestPyResToolboxMapping:
    def test_common_mappings_present(self):
        for unit in ["mD", "psi", "bbl", "ft", "cP"]:
            assert unit in PYRESTOOLBOX_MAPPING, f"Missing mapping: {unit}"

    def test_mapping_values_are_strings(self):
        for unit, const in PYRESTOOLBOX_MAPPING.items():
            assert isinstance(const, str), f"{unit} mapping not string"


class TestBracketNotationRegex:
    def test_matches_simple(self):
        m = re.search(BRACKET_NOTATION_REGEX, "9.81[m/s**2]")
        assert m is not None
        assert m.group(1) == "9.81"
        assert m.group(2) == "m/s**2"

    def test_matches_scientific_notation(self):
        m = re.search(BRACKET_NOTATION_REGEX, "3.14e-2[Pa]")
        assert m is not None
        assert m.group(1) == "3.14e-2"

    def test_matches_with_space(self):
        m = re.search(BRACKET_NOTATION_REGEX, "1.0 [bbl/day]")
        assert m is not None

    def test_no_match_without_brackets(self):
        m = re.search(BRACKET_NOTATION_REGEX, "9.81")
        assert m is None


class TestValidateUnitExpression:
    def test_valid_simple(self):
        result = validate_unit_expression("9.81[m/s**2]")
        assert result["valid"] is True
        assert len(result["unknown"]) == 0

    def test_valid_with_prefix(self):
        result = validate_unit_expression("3.0[km]")
        assert result["valid"] is True

    def test_invalid_unit(self):
        result = validate_unit_expression("1.0[foobar]")
        assert result["valid"] is False
        assert "foobar" in result["unknown"]

    def test_no_brackets_returns_valid(self):
        result = validate_unit_expression("9.81")
        assert result["valid"] is True
        assert result["units_found"] == []
