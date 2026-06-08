"""JSON-based caching for the parsed schema model."""

from __future__ import annotations

import json
from pathlib import Path

from agents4geos.geos.schema.model import (
    SchemaAttribute,
    SchemaElement,
    SchemaModel,
    SchemaType,
)


class SchemaCache:
    """Serialize/deserialize SchemaModel to/from JSON for fast startup."""

    @staticmethod
    def save(model: SchemaModel, cache_path: Path) -> None:
        data = {
            "types": {n: _type_to_dict(t) for n, t in model.types.items()},
            "elements": {n: _element_to_dict(e) for n, e in model.elements.items()},
            "root_name": model.root.name if model.root else None,
        }
        cache_path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load(cache_path: Path) -> SchemaModel:
        data = json.loads(cache_path.read_text())
        types = {n: _dict_to_type(d) for n, d in data["types"].items()}
        elements: dict[str, SchemaElement] = {}
        for n, d in data["elements"].items():
            elements[n] = _dict_to_element(d, types)
        # Re-link children by name
        for n, d in data["elements"].items():
            elements[n].children = [
                elements[cn] for cn in d.get("child_names", []) if cn in elements
            ]
        root_name = data.get("root_name")
        root = elements.get(root_name) if root_name else None
        return SchemaModel(types=types, elements=elements, root=root)

    @staticmethod
    def is_stale(cache_path: Path, schema_path: Path) -> bool:
        if not cache_path.exists():
            return True
        return cache_path.stat().st_mtime < schema_path.stat().st_mtime


def _type_to_dict(t: SchemaType) -> dict:
    return {"name": t.name, "base": t.base, "pattern": t.pattern, "enumeration": t.enumeration}


def _dict_to_type(d: dict) -> SchemaType:
    return SchemaType(
        name=d["name"], base=d["base"], pattern=d.get("pattern"), enumeration=d.get("enumeration", [])
    )


def _element_to_dict(e: SchemaElement) -> dict:
    return {
        "name": e.name,
        "type_name": e.type_name,
        "attributes": [_attr_to_dict(a) for a in e.attributes],
        "child_names": [c.name for c in e.children],
        "min_occurs": e.min_occurs,
        "max_occurs": e.max_occurs,
        "description": e.description,
    }


def _attr_to_dict(a: SchemaAttribute) -> dict:
    return {
        "name": a.name,
        "type_name": a.type_name,
        "required": a.required,
        "default": a.default,
        "description": a.description,
    }


def _dict_to_element(d: dict, types: dict[str, SchemaType]) -> SchemaElement:
    attrs = [
        SchemaAttribute(
            name=ad["name"],
            type_name=ad["type_name"],
            type_ref=types.get(ad["type_name"]),
            required=ad["required"],
            default=ad.get("default"),
            description=ad.get("description", ""),
        )
        for ad in d.get("attributes", [])
    ]
    return SchemaElement(
        name=d["name"],
        type_name=d["type_name"],
        attributes=attrs,
        children=[],  # re-linked after all elements loaded
        min_occurs=d.get("min_occurs", 0),
        max_occurs=d.get("max_occurs"),
        description=d.get("description", ""),
    )
