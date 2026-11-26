import asyncio
import logging
import uuid

from fastapi import APIRouter

router = APIRouter()
log = logging.getLogger("agentshield.eval")


@router.post("/api/eval/run")
async def run_eval(mode: str = "shield"):
    eval_run_id = str(uuid.uuid4())
    asyncio.create_task(_run_bg(mode, eval_run_id))
    return {"eval_run_id": eval_run_id, "mode": mode, "status": "started"}


async def _run_bg(mode: str, eval_run_id: str):
    import sys
    from pathlib import Path
    # Ensure eval package is importable
    repo_root = Path(__file__).parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        await asyncio.to_thread(_run_sync, mode, eval_run_id)
    except Exception as e:
        log.error("Eval run %s failed: %s", eval_run_id, e)


def _run_sync(mode: str, eval_run_id: str):
    from eval.runner import run_all, _get_supabase, _write_eval_run
    summaries = run_all([mode])
    # Patch eval_run_id into the written row (best-effort: re-update with the id)
    # The row was already inserted by run_all; tag it if possible
    if mode in summaries:
        sb = _get_supabase()
        if sb:
            try:
                # Find the most recent eval_run for this mode and tag it
                result = sb.table("eval_runs").select("id").eq("mode", mode).order(
                    "created_at", desc=True
                ).limit(1).execute()
                if result.data:
                    sb.table("eval_runs").update({"id": eval_run_id}).eq(
                        "id", result.data[0]["id"]
                    ).execute()
            except Exception:
                pass
