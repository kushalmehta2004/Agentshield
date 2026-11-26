from fastapi import APIRouter

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions():
    # Phase 1: implement passthrough proxy
    return {"stub": "Phase 1 not yet implemented"}


@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": []}
