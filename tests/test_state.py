"""Tests for DocumentStore and schema loader."""
from agents4geos.state.documents import DocumentStore
from agents4geos.config import get_schema
from agents4geos.geos.xml.state import DocumentState, ElementState


def test_create_and_get(schema):
    store = DocumentStore()
    root_state = ElementState(schema_element=schema.root)
    doc = DocumentState(root=root_state)
    doc_id = store.create(doc)
    assert doc_id.startswith("doc_")
    retrieved = store.get(doc_id)
    assert retrieved is doc


def test_get_nonexistent():
    store = DocumentStore()
    assert store.get("doc_nonexistent") is None


def test_remove(schema):
    store = DocumentStore()
    root_state = ElementState(schema_element=schema.root)
    doc = DocumentState(root=root_state)
    doc_id = store.create(doc)
    removed = store.remove(doc_id)
    assert removed is True
    assert store.get(doc_id) is None


def test_list_documents(schema):
    store = DocumentStore()
    root_state = ElementState(schema_element=schema.root)
    id1 = store.create(DocumentState(root=root_state))
    id2 = store.create(DocumentState(root=root_state))
    docs = store.list()
    assert id1 in docs
    assert id2 in docs


def test_get_schema_returns_model():
    model = get_schema()
    assert model.root is not None
    assert model.root.name == "Problem"
