"""Shared test fixtures for Agents4GEOS."""
from __future__ import annotations
from pathlib import Path
import pytest
from geos_tui.schema.model import SchemaModel

from agents4geos.config import get_schema

@pytest.fixture(scope="session")
def schema() -> SchemaModel:
    """Session-scoped schema. Sourced from GEOS_SCHEMA or the on-disk cache."""
    return get_schema()

@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path
