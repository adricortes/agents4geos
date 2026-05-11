"""Server configuration and schema path resolution."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

from geos_tui.schema.parser import SchemaParser
from geos_tui.schema.model import SchemaModel
from geos_tui.schema.cache import SchemaCache

def _default_schema_path() -> Path:
    env = os.environ.get("GEOS_SCHEMA")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "geos-tui" / "geos" / "build" / "schema.xsd"

def _default_cache_dir() -> Path:
    return Path(__file__).resolve().parent / ".cache"

@dataclass
class ServerConfig:
    schema_path: Path = field(default_factory=_default_schema_path)
    cache_dir: Path = field(default_factory=_default_cache_dir)

_schema_cache: SchemaModel | None = None

def get_schema() -> SchemaModel:
    """Return cached SchemaModel, parsing/loading as needed."""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    cfg = ServerConfig()
    cache_file = cfg.cache_dir / "schema.json"
    schema_exists = cfg.schema_path.exists()
    cache_exists = cache_file.exists()
    if cache_exists and (not schema_exists or not SchemaCache.is_stale(cache_file, cfg.schema_path)):
        _schema_cache = SchemaCache.load(cache_file)
    else:
        _schema_cache = SchemaParser(cfg.schema_path).parse()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        SchemaCache.save(_schema_cache, cache_file)
    return _schema_cache
