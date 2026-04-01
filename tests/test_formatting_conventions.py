"""Tests for formatting conventions knowledge module."""
import re
import pytest
from agents4geosx.knowledge.formatting_conventions import (
    DEFAULT_FORMAT,
    ATTRIBUTE_FORMATTING,
    PROTECTED_EXPRESSIONS,
)


class TestDefaultFormat:
    def test_indent(self):
        assert DEFAULT_FORMAT["indent"] == 2

    def test_style(self):
        assert DEFAULT_FORMAT["style"] == "fixed"

    def test_block_separation(self):
        assert DEFAULT_FORMAT["block_separation_max_depth"] == 2

    def test_sort_attributes(self):
        assert DEFAULT_FORMAT["sort_attributes"] is False

    def test_close_tag_newline(self):
        assert DEFAULT_FORMAT["close_tag_newline"] is False


class TestAttributeFormatting:
    def test_comma_spacing_pattern_compiles(self):
        p = ATTRIBUTE_FORMATTING["comma_spacing"]
        re.compile(p["pattern"])

    def test_comma_spacing_replacement(self):
        p = ATTRIBUTE_FORMATTING["comma_spacing"]
        result = re.sub(p["pattern"], p["replacement"], "a,b,  c")
        assert result == "a, b, c"

    def test_brace_opening(self):
        p = ATTRIBUTE_FORMATTING["brace_opening"]
        result = re.sub(p["pattern"], p["replacement"], "{value")
        assert result == "{ value"

    def test_brace_closing(self):
        p = ATTRIBUTE_FORMATTING["brace_closing"]
        result = re.sub(p["pattern"], p["replacement"], "value}")
        assert result == "value }"

    def test_whitespace_consolidation(self):
        p = ATTRIBUTE_FORMATTING["whitespace_consolidation"]
        result = re.sub(p["pattern"], p["replacement"], "a  b   c")
        assert result == "a b c"


class TestProtectedExpressions:
    def test_symbolic_function_protected(self):
        elements = [p["element"] for p in PROTECTED_EXPRESSIONS]
        assert "SymbolicFunction" in elements

    def test_composite_function_protected(self):
        elements = [p["element"] for p in PROTECTED_EXPRESSIONS]
        assert "CompositeFunction" in elements

    def test_expression_attribute(self):
        for entry in PROTECTED_EXPRESSIONS:
            assert entry["attribute"] == "expression"
