"""Runtime document state for the TUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from geos_tui.schema.model import SchemaElement


@dataclass
class ValidationError:
    """A validation error for a specific field."""

    element_path: str
    attribute_name: str
    message: str


@dataclass
class ElementState:
    """Runtime state of a single XML element in the TUI."""

    schema_element: SchemaElement
    attributes: dict[str, str] = field(default_factory=dict)
    children: list[ElementState] = field(default_factory=list)
    read_only: bool = False
    opaque_node: etree._Element | None = None
    comments: list[str] = field(default_factory=list)


@dataclass
class DocumentState:
    """The complete state of the XML document being edited."""

    root: ElementState
    source_path: Path | None = None
    is_modified: bool = False
    validation_errors: list[ValidationError] = field(default_factory=list)
