from fastapi import APIRouter

router = APIRouter()


@router.post("/api/eval/run")
async def run_eval(mode: str = "shield"):
    # Phase 5: run eval suite in background
    return {"stub": "Phase 5 not yet implemented"}
