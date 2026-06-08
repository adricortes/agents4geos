"""Dataclasses representing the parsed XSD schema structure."""

from __future__ import annotations

from dataclasses import dataclass, field

# Pattern prefix that GEOS uses to allow symbolic expressions in any field
_EXPRESSION_PREFIX = r".*[\[\]`$].*"


@dataclass
class SchemaType:
    """A simple type from the XSD (e.g., real64, groupName, R1Tensor)."""

    name: str
    base: str
    pattern: str | None = None
    enumeration: list[str] = field(default_factory=list)

    @property
    def has_expression_passthrough(self) -> bool:
        """Whether this type allows GEOS symbolic expressions."""
        if self.pattern is None:
            return False
        return _EXPRESSION_PREFIX in self.pattern


@dataclass
class SchemaAttribute:
    """An attribute on a complex type (maps to an XML attribute)."""

    name: str
    type_name: str
    type_ref: SchemaType | None = None
    required: bool = False
    default: str | None = None
    description: str = ""


@dataclass
class SchemaElement:
    """A complex type element (e.g., SinglePhaseFVM, CompressibleSinglePhaseFluid)."""

    name: str
    type_name: str
    attributes: list[SchemaAttribute] = field(default_factory=list)
    children: list[SchemaElement] = field(default_factory=list)
    min_occurs: int = 0
    max_occurs: int | None = None  # None = unbounded
    description: str = ""


@dataclass
class SchemaModel:
    """The complete parsed schema."""

    types: dict[str, SchemaType] = field(default_factory=dict)
    elements: dict[str, SchemaElement] = field(default_factory=dict)
    root: SchemaElement | None = None
