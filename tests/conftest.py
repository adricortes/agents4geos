"""Shared test fixtures for Agents4GEOSX."""
from __future__ import annotations
from pathlib import Path
import pytest
from geos_tui.schema.parser import SchemaParser
from geos_tui.schema.model import SchemaModel
from geos_tui.schema.cache import SchemaCache

SCHEMA_PATH = Path(__file__).resolve().parents[1] / ".." / ".." / "geos-tui" / "geos" / "build" / "schema.xsd"
CACHE_PATH = Path(__file__).resolve().parents[1] / "src" / "agents4geosx" / ".cache" / "schema.json"

@pytest.fixture(scope="session")
def schema() -> SchemaModel:
    if CACHE_PATH.exists() and not SchemaCache.is_stale(CACHE_PATH, SCHEMA_PATH):
        return SchemaCache.load(CACHE_PATH)
    model = SchemaParser(SCHEMA_PATH).parse()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SchemaCache.save(model, CACHE_PATH)
    return model

@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path
