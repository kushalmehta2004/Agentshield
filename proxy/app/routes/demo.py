from fastapi import APIRouter

router = APIRouter()


@router.get("/demo/{page}")
async def demo_page(page: str):
    # Phase 2: serve demo site pages
    return {"stub": f"demo/{page} — Phase 2 not yet implemented"}


@router.post("/api/scenarios/{name}/run")
async def run_scenario(name: str, mode: str = "shield"):
    # Phase 2: run scenario server-side
    return {"stub": "Phase 2 not yet implemented"}
