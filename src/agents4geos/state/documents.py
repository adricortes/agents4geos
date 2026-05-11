"""In-memory document store for stateful XML assembly."""
from __future__ import annotations
import uuid
from geos_tui.xml.state import DocumentState


class DocumentStore:
    """Holds DocumentState objects keyed by doc_id."""

    def __init__(self) -> None:
        self._docs: dict[str, DocumentState] = {}

    def create(self, doc: DocumentState) -> str:
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        self._docs[doc_id] = doc
        return doc_id

    def get(self, doc_id: str) -> DocumentState | None:
        return self._docs.get(doc_id)

    def remove(self, doc_id: str) -> bool:
        return self._docs.pop(doc_id, None) is not None

    def list(self) -> list[str]:
        return list(self._docs.keys())
