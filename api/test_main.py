"""Tests for diagrams API service."""
import json
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    """Health endpoint should return ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_generate_flowchart(client):
    """POST /api/generate with type=flowchart should return excalidraw + svg."""
    payload = {
        "type": "flowchart",
        "data": {
            "nodes": [{"label": "A"}, {"label": "B"}],
            "edges": [{"from": "A", "to": "B"}],
        },
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "excalidraw" in body
    assert "elements" in body["excalidraw"]
    assert "svg" in body
    assert "<svg" in body["svg"]


def test_generate_architecture(client):
    """POST /api/generate with type=architecture should work."""
    payload = {
        "type": "architecture",
        "data": {
            "layers": [
                {"name": "Frontend", "color": "blue", "components": [{"label": "React"}]},
                {"name": "Backend", "color": "green", "components": [{"label": "API"}]},
            ],
            "connections": [{"from": "React", "to": "API"}],
        },
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "excalidraw" in body
    assert "svg" in body


def test_generate_sequence(client):
    """POST /api/generate with type=sequence should work."""
    payload = {
        "type": "sequence",
        "data": {
            "participants": ["Alice", "Bob"],
            "messages": [{"from": "Alice", "to": "Bob", "label": "Hello"}],
        },
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "excalidraw" in body
    assert "svg" in body


def test_generate_mindmap(client):
    """POST /api/generate with type=mindmap should work."""
    payload = {
        "type": "mindmap",
        "data": {
            "root": {"label": "Root", "children": [{"label": "A"}, {"label": "B"}]},
        },
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "excalidraw" in body
    assert "svg" in body


def test_generate_mermaid(client):
    """POST /api/generate with type=mermaid should work."""
    payload = {
        "type": "mermaid",
        "data": {
            "mermaid": "graph LR\n  A[Start] --> B[End]",
        },
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "excalidraw" in body
    assert "svg" in body


def test_generate_unknown_type(client):
    """Unknown diagram type should return 400."""
    payload = {
        "type": "unknown_diagram_type",
        "data": {},
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 400


def test_generate_with_title_and_theme(client):
    """Should accept optional title and theme."""
    payload = {
        "type": "flowchart",
        "data": {
            "nodes": [{"label": "X"}],
            "edges": [],
        },
        "title": "My Diagram",
        "theme": "dark",
    }
    resp = client.post("/api/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "excalidraw" in body
    # Dark theme should have dark background
    bg = body["excalidraw"].get("appState", {}).get("viewBackgroundColor", "")
    assert bg == "#1e1e1e"
