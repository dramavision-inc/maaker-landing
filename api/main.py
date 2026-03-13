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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
                create_flowchart(
                    nodes=req.data.get("nodes", []),
                    edges=req.data.get("edges", []),
                    direction=req.data.get("direction", "LR"),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "architecture":
                create_architecture_diagram(
                    layers=req.data.get("layers", []),
                    connections=req.data.get("connections"),
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "sequence":
                create_sequence_diagram(
                    participants=req.data.get("participants", []),
                    messages=req.data.get("messages", []),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "mindmap":
                create_mindmap_diagram(
                    root=req.data.get("root", {"label": "Root"}),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "mermaid":
                import_mermaid(
                    mermaid=req.data.get("mermaid", ""),
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
