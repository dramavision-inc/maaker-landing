"""Diagrams API — FastAPI wrapper for excalidraw-mcp engine functions."""

import json
import tempfile
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from excalidraw_mcp.tools.flowchart import create_flowchart
from excalidraw_mcp.tools.architecture import create_architecture_diagram
from excalidraw_mcp.tools.sequence import create_sequence_diagram
from excalidraw_mcp.tools.mindmap import create_mindmap_diagram
from excalidraw_mcp.tools.mermaid import import_mermaid
from excalidraw_mcp.utils.svg_export import export_to_svg

app = FastAPI(title="Diagrams API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://maaker.ai",
        "https://diagrams.maaker.ai",
        "http://localhost:8080",
    ],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class GenerateRequest(BaseModel):
    type: str
    data: dict[str, Any]
    title: Optional[str] = None
    theme: str = "light"


class GenerateResponse(BaseModel):
    excalidraw: dict[str, Any]
    svg: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Generate a diagram and return Excalidraw JSON + SVG."""
    with tempfile.TemporaryDirectory() as tmp:
        output_path = f"{tmp}/diagram.excalidraw"

        try:
            if req.type == "flowchart":
                # Normalize nodes: accept ["A", "B"] or [{"label": "A"}, ...]
                raw_nodes = req.data.get("nodes", [])
                nodes = [{"label": n} if isinstance(n, str) else n for n in raw_nodes]
                # Normalize edges: accept {"from": "A", "to": "B"} as-is
                edges = req.data.get("edges", [])
                create_flowchart(
                    nodes=nodes,
                    edges=edges,
                    direction=req.data.get("direction", "LR"),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "architecture":
                # Normalize layers: components can be strings or dicts
                raw_layers = req.data.get("layers", [])
                layers = []
                for layer in raw_layers:
                    comps = layer.get("components", [])
                    normalized_comps = [{"label": c} if isinstance(c, str) else c for c in comps]
                    layers.append({**layer, "components": normalized_comps})
                create_architecture_diagram(
                    layers=layers,
                    connections=req.data.get("connections"),
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "sequence":
                # Normalize messages: "message" → "label"
                raw_msgs = req.data.get("messages", [])
                messages = []
                for m in raw_msgs:
                    msg = dict(m)
                    if "message" in msg and "label" not in msg:
                        msg["label"] = msg.pop("message")
                    messages.append(msg)
                create_sequence_diagram(
                    participants=req.data.get("participants", []),
                    messages=messages,
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "mindmap":
                # Normalize root: accept string + items list → nested tree
                raw_root = req.data.get("root", {"label": "Root"})
                if isinstance(raw_root, str):
                    root = {"label": raw_root, "children": []}
                    # Convert flat items like ["ML > 监督学习", "ML > 无监督学习"] to tree
                    for item in req.data.get("items", []):
                        parts = [p.strip() for p in item.split(">")]
                        node = root
                        for part in parts:
                            existing = next((c for c in node.get("children", []) if c["label"] == part), None)
                            if existing:
                                node = existing
                            else:
                                child = {"label": part, "children": []}
                                node.setdefault("children", []).append(child)
                                node = child
                else:
                    root = raw_root
                create_mindmap_diagram(
                    root=root,
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "mermaid":
                # Accept both "mermaid" and "code" field names
                mermaid_code = req.data.get("mermaid") or req.data.get("code", "")
                import_mermaid(
                    mermaid=mermaid_code,
                    output_path=output_path,
                    theme=req.theme,
                )
            else:
                raise HTTPException(status_code=400, detail=f"Unknown diagram type: {req.type}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # Read the generated file
        with open(output_path) as f:
            excalidraw_data = json.load(f)

        # Generate SVG
        svg = export_to_svg(excalidraw_data)

    return GenerateResponse(excalidraw=excalidraw_data, svg=svg)
