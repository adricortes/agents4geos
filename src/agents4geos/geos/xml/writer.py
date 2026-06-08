"""Serialize DocumentState back to GEOS XML."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from agents4geos.geos.xml.state import DocumentState, ElementState


class XMLWriter:
    """Writes a DocumentState to a GEOS XML file."""

    def save(self, state: DocumentState, path: Path) -> None:
        xml_root = self._build_element(state.root)
        tree = etree.ElementTree(xml_root)
        tree.write(
            str(path),
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        )

    def _build_element(self, es: ElementState) -> etree._Element:
        # Opaque elements: re-insert the original lxml node
        if es.opaque_node is not None:
            return es.opaque_node

        elem = etree.Element(es.schema_element.name)

        # Set attributes
        for key, value in es.attributes.items():
            elem.set(key, value)

        # Add comments
        for comment_text in es.comments:
            elem.append(etree.Comment(f" {comment_text} "))

        # Add child elements
        for child_state in es.children:
            child_elem = self._build_element(child_state)
            elem.append(child_elem)

        return elem
