"""
Fallback Web Server for ArchForge.
Allows interacting with ArchForge Code Agent via web browser.
"""

from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from archforge.agent.events import AgentEvent, EventBus, EventType
from archforge.agent.generator import ProjectGenerator
from archforge.config import AgentConfig
from archforge.llm.deepseek_client import DeepSeekClient

import sys

app = FastAPI(title="ArchForge Web UI (Fallback)")


def _resolve_static_index() -> Path:
    if hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / "archforge" / "web" / "static" / "index.html"
        if p.exists():
            return p
    local_p = Path(__file__).parent / "static" / "index.html"
    return local_p


INDEX_FILE = _resolve_static_index()

# State management
current_event_bus = EventBus()
current_cancel_event = threading.Event()
worker_thread: Optional[threading.Thread] = None
accumulated_events: List[Dict[str, Any]] = []
is_generating: bool = False


class GenerateRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    doc_path: str = "samples/Architecture_Documentation.md"
    views_path: str = "samples/Architecture_View.md"
    out_path: str = "generated_project"


class TestConnectionRequest(BaseModel):
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"


@app.get("/", response_class=HTMLResponse)
def get_index():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="Web UI static index file not found")
    return FileResponse(INDEX_FILE)


@app.get("/api/config")
def get_config():
    cfg = AgentConfig.load()
    return {
        "masked_key": cfg.get_masked_api_key(),
        "model": cfg.model,
        "base_url": cfg.base_url,
    }


@app.post("/api/test-connection")
def test_connection(req: TestConnectionRequest):
    client = DeepSeekClient(api_key=req.api_key, base_url=req.base_url, model=req.model)
    try:
        ok, msg = client.test_connection()
        return {"success": ok, "message": msg}
    finally:
        client.close()


@app.post("/api/generate")
def start_generation(req: GenerateRequest):
    global is_generating, worker_thread, current_event_bus, current_cancel_event, accumulated_events

    if is_generating:
        return {"success": False, "message": "Generation already in progress"}

    accumulated_events.clear()
    current_cancel_event.clear()
    current_event_bus = EventBus()

    # Event accumulator
    def on_event(ev: AgentEvent):
        accumulated_events.append(ev.to_dict())

    current_event_bus.subscribe(on_event)

    cfg = AgentConfig.load()
    if req.api_key:
        cfg.api_key = req.api_key
    if req.model:
        cfg.model = req.model
    if req.base_url:
        cfg.base_url = req.base_url

    doc_p = Path(req.doc_path).resolve()
    views_p = Path(req.views_path).resolve()
    out_p = Path(req.out_path).resolve()

    if not doc_p.exists():
        raise HTTPException(status_code=400, detail=f"Doc file not found: {doc_p}")
    if not views_p.exists():
        raise HTTPException(status_code=400, detail=f"Views file not found: {views_p}")

    def run_worker():
        global is_generating
        is_generating = True
        try:
            gen = ProjectGenerator(
                doc_path=doc_p,
                views_path=views_p,
                output_dir=out_p,
                config=cfg,
                event_bus=current_event_bus,
                cancel_event=current_cancel_event,
            )
            gen.run()
        finally:
            is_generating = False

    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()

    return {"success": True, "message": "Generation started in background."}


@app.post("/api/cancel")
def cancel_generation():
    global current_cancel_event
    current_cancel_event.set()
    return {"success": True, "message": "Cancellation signaled"}


@app.get("/api/events")
def get_events():
    global accumulated_events
    events_copy = list(accumulated_events)
    accumulated_events.clear()
    return {"events": events_copy, "is_generating": is_generating}


def run_web(host: str = "127.0.0.1", port: int = 5000):
    import uvicorn
    print(f"ArchForge Web UI running at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_web()
