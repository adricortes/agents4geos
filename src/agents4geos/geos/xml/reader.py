"""Load a GEOS XML input file into a DocumentState."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from geos_tui.schema.model import SchemaElement, SchemaModel
from geos_tui.xml.state import DocumentState, ElementState


class XMLReader:
    """Reads a GEOS XML file and maps it to a DocumentState."""

    def __init__(self, schema: SchemaModel) -> None:
        self._schema = schema

    def load(self, path: Path) -> DocumentState:
        parser = etree.XMLParser(remove_comments=False)
        tree = etree.parse(str(path), parser)
        xml_root = tree.getroot()

        root_state = self._read_element(xml_root, self._schema.root)
        return DocumentState(root=root_state, source_path=path, is_modified=False)

    def _read_element(
        self, xml_elem: etree._Element, schema_elem: SchemaElement | None
    ) -> ElementState:
        if schema_elem is None:
            # Unknown element — preserve as opaque
            placeholder = SchemaElement(
                name=xml_elem.tag,
                type_name="",
                attributes=[],
                children=[],
                min_occurs=0,
                max_occurs=None,
                description="",
            )
            return ElementState(
                schema_element=placeholder,
                attributes=dict(xml_elem.attrib),
                read_only=True,
                opaque_node=xml_elem,
            )

        # Read attributes from XML
        attributes: dict[str, str] = {}
        for key, value in xml_elem.attrib.items():
            attributes[key] = value

        # Read child elements
        children: list[ElementState] = []
        comments: list[str] = []
        for child_node in xml_elem:
            if isinstance(child_node, etree._Comment):
                comments.append(child_node.text.strip())
                continue
            # Try to match child to schema
            child_schema = self._find_child_schema(schema_elem, child_node.tag)
            child_state = self._read_element(child_node, child_schema)
            children.append(child_state)

        return ElementState(
            schema_element=schema_elem,
            attributes=attributes,
            children=children,
            read_only=False,
            comments=comments,
        )

    @staticmethod
    def _find_child_schema(
        parent: SchemaElement, child_tag: str
    ) -> SchemaElement | None:
        """Find the schema definition for a child element by tag name."""
        # Direct children
        for child in parent.children:
            if child.name == child_tag:
                return child
            # Also check grandchildren (e.g., Solvers > SinglePhaseFVM > LinearSolverParameters)
            for grandchild in child.children:
                if grandchild.name == child_tag:
                    return grandchild
        return None
