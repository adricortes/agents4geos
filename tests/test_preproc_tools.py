"""Tests for preprocessing MCP tools."""
from __future__ import annotations

import pytest
from agents4geosx.tools.preproc_tools import convert_units


class TestConvertUnits:
    def test_si_base_no_conversion(self):
        result = convert_units("9.81[m/s**2]")
        assert result["valid"] is True
        assert result["numeric_value"] == 9.81
        assert result["unit_expression"] == "m/s**2"
        assert abs(result["si_value"] - 9.81) < 1e-10

    def test_millidarcy(self):
        result = convert_units("100[mD]")
        assert result["valid"] is True
        assert result["numeric_value"] == 100.0
        # 1 mD = milli (1e-3) * darcy (9.869233e-13) = 9.869233e-16 m^2
        # 100 mD = 9.869233e-14 m^2
        expected = 100 * 1e-3 * 9.869233e-13
        assert abs(result["si_value"] - expected) / expected < 1e-4

    def test_prefix_kilo(self):
        result = convert_units("3.0[km]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 3000.0) < 1e-10

    def test_prefix_mega_pascal(self):
        result = convert_units("20[MPa]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 20e6) < 1e-2

    def test_psi(self):
        result = convert_units("1000[psi]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 6894760.0) < 100

    def test_barrel_per_day(self):
        result = convert_units("1.0[bbl/day]")
        assert result["valid"] is True
        expected = 0.1589873 / 86400.0
        assert abs(result["si_value"] - expected) / expected < 1e-4

    def test_scientific_notation_input(self):
        result = convert_units("3.14e-2[Pa]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 3.14e-2) < 1e-10

    def test_invalid_unit(self):
        result = convert_units("1.0[foobar]")
        assert result["valid"] is False
        assert "foobar" in result["unknown_units"]

    def test_no_brackets(self):
        result = convert_units("plain text")
        assert result["valid"] is True
        assert result["si_value"] is None

    def test_space_before_bracket(self):
        result = convert_units("1.0 [bbl]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 0.1589873) < 1e-6

    def test_centipoise(self):
        result = convert_units("1.0[cP]")
        assert result["valid"] is True
        # centi (1e-2) * poise (0.1) = 0.001 Pa·s
        assert abs(result["si_value"] - 0.001) < 1e-10

    def test_foot(self):
        result = convert_units("100[ft]")
        assert result["valid"] is True
        assert abs(result["si_value"] - 30.48) < 1e-6
