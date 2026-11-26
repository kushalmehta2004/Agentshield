import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

DEMO_DIR = Path(__file__).parent.parent.parent / "demo_site"

PAGES = {
    "team-update", "evil-blog", "evil-blog-v2", "hidden-html",
    "benign-page-1", "benign-page-2", "benign-page-3", "benign-page-4",
    "attack-split-1", "attack-split-2", "attack-http-post", "attack-whitespace",
    "attack-paraphrased-2", "attack-paraphrased-3", "attack-html-comment-2",
    "attack-obvious-2",
}


@router.get("/demo/{page}", response_class=HTMLResponse)
async def demo_page(page: str):
    if page not in PAGES:
        raise HTTPException(status_code=404, detail=f"Demo page '{page}' not found.")
    path = DEMO_DIR / f"{page}.html"
    return HTMLResponse(content=path.read_text(encoding="utf-8"))


@router.post("/api/scenarios/{name}/run")
async def run_scenario(name: str, mode: str = "shield"):
    from agent.scenarios import SCENARIOS
    if name not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found.")
    session_id = str(uuid.uuid4())
    # Pre-create the session row so the dashboard can navigate to it immediately
    from app import logger as db
    db.log_session(session_id, name, mode)
    # Run agent in background so the HTTP response returns immediately
    asyncio.create_task(_run_bg(name, mode, session_id))
    return {"session_id": session_id, "scenario": name, "mode": mode}


async def _run_bg(name: str, mode: str, session_id: str):
    from agent.scenarios import SCENARIOS
    from agent.loop import run_scenario as _run
    try:
        await asyncio.to_thread(_run, name, mode, session_id)
    except Exception as e:
        import logging
        logging.getLogger("agentshield.demo").error("Scenario %s failed: %s", name, e)
