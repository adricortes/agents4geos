"""Server configuration and schema path resolution."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

from geos_tui.schema.parser import SchemaParser
from geos_tui.schema.model import SchemaModel
from geos_tui.schema.cache import SchemaCache

def _default_schema_path() -> Path | None:
    env = os.environ.get("GEOS_SCHEMA")
    return Path(env) if env else None

def _default_cache_dir() -> Path:
    return Path(__file__).resolve().parent / ".cache"

@dataclass
class ServerConfig:
    schema_path: Path | None = field(default_factory=_default_schema_path)
    cache_dir: Path = field(default_factory=_default_cache_dir)

_schema_cache: SchemaModel | None = None

def get_schema() -> SchemaModel:
    """Return cached SchemaModel, parsing/loading as needed.

    The schema source is taken from GEOS_SCHEMA. If unset, the on-disk cache
    (src/agents4geos/.cache/schema.json) is the only fallback — there is no
    hardcoded path, since the schema.xsd is a GEOS build artifact whose
    location varies between machines.
    """
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    cfg = ServerConfig()
    cache_file = cfg.cache_dir / "schema.json"
    schema_path = cfg.schema_path
    schema_exists = schema_path is not None and schema_path.exists()
    cache_exists = cache_file.exists()
    # Cache is usable if the source schema is missing or unchanged since cache write.
    if cache_exists and (not schema_exists or not SchemaCache.is_stale(cache_file, schema_path)):  # type: ignore[arg-type]
        _schema_cache = SchemaCache.load(cache_file)
        return _schema_cache
    if schema_path is None:
        raise FileNotFoundError(
            "GEOS_SCHEMA is not set and no cached schema is available. "
            "Set GEOS_SCHEMA to a built GEOS schema.xsd "
            "(e.g. /path/to/GEOS/build/schema.xsd)."
        )
    if not schema_exists:
        raise FileNotFoundError(
            f"GEOS_SCHEMA is set to {str(schema_path)!r} but no file exists there. "
            f"Point it at a built GEOS schema.xsd."
        )
    _schema_cache = SchemaParser(schema_path).parse()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    SchemaCache.save(_schema_cache, cache_file)
    return _schema_cache
