import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AgentShield Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("DASHBOARD_ORIGIN", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes import chat, demo, eval as eval_router  # noqa: E402

app.include_router(chat.router)
app.include_router(demo.router)
app.include_router(eval_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
