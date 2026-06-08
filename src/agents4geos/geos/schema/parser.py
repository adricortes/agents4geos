"""Parse GEOS XSD schema into a SchemaModel."""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from agents4geos.geos.schema.model import (
    SchemaAttribute,
    SchemaElement,
    SchemaModel,
    SchemaType,
)

XSD_NS = "http://www.w3.org/2001/XMLSchema"
XSD = f"{{{XSD_NS}}}"


class SchemaParser:
    """Parses a GEOS XSD schema file into a SchemaModel."""

    def __init__(self, schema_path: Path) -> None:
        self._path = schema_path
        self._tree = etree.parse(str(schema_path))
        self._root = self._tree.getroot()
        self._types: dict[str, SchemaType] = {}
        self._complex_types: dict[str, etree._Element] = {}
        self._elements: dict[str, SchemaElement] = {}
        self._building: set[str] = set()  # cycle detection for recursive types

    def parse(self) -> SchemaModel:
        """Parse the full schema and return a SchemaModel."""
        self._parse_simple_types()
        self._parse_complex_types()
        root = self._elements.get("Problem")
        return SchemaModel(types=self._types, elements=self._elements, root=root)

    def _parse_simple_types(self) -> None:
        """Extract all xsd:simpleType definitions."""
        for st in self._root.iterchildren(f"{XSD}simpleType"):
            name = st.get("name")
            if name is None:
                continue
            restriction = st.find(f"{XSD}restriction")
            if restriction is None:
                continue
            base = restriction.get("base", "xsd:string")
            pattern_elem = restriction.find(f"{XSD}pattern")
            pattern = pattern_elem.get("value") if pattern_elem is not None else None
            enumeration = self._extract_enum_values(pattern)
            self._types[name] = SchemaType(
                name=name, base=base, pattern=pattern, enumeration=enumeration
            )

    @staticmethod
    def _extract_enum_values(pattern: str | None) -> list[str]:
        """Extract enum-like values from a pattern.

        GEOS patterns look like: .*[\\[\\]`$].*|value1|value2|value3
        The first alternative is the expression passthrough; the rest are
        literal allowed values (if they don't contain regex metacharacters).
        """
        if pattern is None:
            return []
        parts = pattern.split("|")
        values = []
        for part in parts:
            part = part.strip()
            # Skip the expression passthrough pattern
            if r"[\[\]`$]" in part or part == "":
                continue
            # Skip patterns with regex metacharacters (actual regex, not enum values)
            if re.search(r"[\\()+*?{}^\[\]]", part):
                continue
            values.append(part)
        return values

    def _parse_complex_types(self) -> None:
        """Parse all xsd:complexType definitions and build the element tree."""
        # Index complex types by name
        for ct in self._root.iterchildren(f"{XSD}complexType"):
            name = ct.get("name")
            if name is not None:
                self._complex_types[name] = ct

        # Parse ProblemType to build the root element tree
        problem_ct = self._complex_types.get("ProblemType")
        if problem_ct is not None:
            self._elements["Problem"] = self._build_element(
                name="Problem",
                type_name="ProblemType",
                ct=problem_ct,
                min_occurs=1,
                max_occurs=1,
            )

    def _build_element(
        self,
        name: str,
        type_name: str,
        ct: etree._Element,
        min_occurs: int = 0,
        max_occurs: int | None = None,
    ) -> SchemaElement:
        """Build a SchemaElement from a complex type definition."""
        self._building.add(type_name)
        attributes = self._parse_attributes(ct)
        children = self._parse_child_elements(ct)
        self._building.discard(type_name)
        element = SchemaElement(
            name=name,
            type_name=type_name,
            attributes=attributes,
            children=children,
            min_occurs=min_occurs,
            max_occurs=max_occurs,
            description="",
        )
        self._elements[name] = element
        return element

    def _parse_attributes(self, ct: etree._Element) -> list[SchemaAttribute]:
        """Parse all xsd:attribute children of a complex type."""
        attrs = []
        for attr_elem in ct.iterchildren(f"{XSD}attribute"):
            attr_name = attr_elem.get("name", "")
            type_name = attr_elem.get("type", "xsd:string")
            required = attr_elem.get("use") == "required"
            default = attr_elem.get("default")
            description = self._extract_comment_description(attr_elem)
            type_ref = self._types.get(type_name)
            attrs.append(
                SchemaAttribute(
                    name=attr_name,
                    type_name=type_name,
                    type_ref=type_ref,
                    required=required,
                    default=default,
                    description=description,
                )
            )
        return attrs

    def _parse_child_elements(self, ct: etree._Element) -> list[SchemaElement]:
        """Parse child element definitions from xsd:choice or xsd:sequence."""
        children = []
        for choice in ct.iterchildren(f"{XSD}choice"):
            for elem in choice.iterchildren(f"{XSD}element"):
                child = self._parse_element_ref(elem)
                if child is not None:
                    children.append(child)
        for seq in ct.iterchildren(f"{XSD}sequence"):
            for elem in seq.iterchildren(f"{XSD}element"):
                child = self._parse_element_ref(elem)
                if child is not None:
                    children.append(child)
        return children

    def _parse_element_ref(self, elem: etree._Element) -> SchemaElement | None:
        """Parse a single xsd:element inside a choice/sequence."""
        name = elem.get("name")
        type_name = elem.get("type", "")
        if name is None:
            return None

        min_occ_str = elem.get("minOccurs", "0")
        max_occ_str = elem.get("maxOccurs", "1")
        min_occurs = int(min_occ_str)
        max_occurs = None if max_occ_str == "unbounded" else int(max_occ_str)

        # Resolve the complex type (with cycle detection)
        ct = self._complex_types.get(type_name)
        if ct is not None:
            if type_name in self._building:
                # Circular reference — return leaf to break the cycle
                return SchemaElement(
                    name=name,
                    type_name=type_name,
                    attributes=self._parse_attributes(ct),
                    children=[],
                    min_occurs=min_occurs,
                    max_occurs=max_occurs,
                    description="",
                )
            return self._build_element(name, type_name, ct, min_occurs, max_occurs)

        # No complex type found — leaf element
        return SchemaElement(
            name=name,
            type_name=type_name,
            attributes=[],
            children=[],
            min_occurs=min_occurs,
            max_occurs=max_occurs,
            description="",
        )

    @staticmethod
    def _extract_comment_description(attr_elem: etree._Element) -> str:
        """Extract description from the XML comment preceding an attribute.

        GEOS schema uses: <!--attrName => description text-->
        placed immediately before the xsd:attribute element.
        """
        prev = attr_elem.getprevious()
        if prev is not None and isinstance(prev, etree._Comment):
            text = prev.text.strip()
            match = re.match(r"(\w+)\s*=>\s*(.*)", text, re.DOTALL)
            if match:
                return match.group(2).strip()
        return ""
