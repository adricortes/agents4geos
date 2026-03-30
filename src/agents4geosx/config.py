"""Server configuration and schema path resolution."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

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
