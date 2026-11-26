# AgentShield — Working Notes

## What this is
A security proxy for AI agents with a "Proof of Cause" engine. See AGENTSHIELD_PRD.md for the full spec.

## Current phase
**Phase 2 — COMPLETE. Awaiting Kushal approval + attack verification before Phase 3.**

## Run commands
```bash
# Proxy (from repo root)
cd proxy && uv run uvicorn app.main:app --reload --port 8000

# Tests
cd proxy && uv run pytest

# Dashboard
cd dashboard && npm run dev

# Agent (run from proxy/)
cd proxy && uv run python -m agent.run --scenario benign_summary_email --mode shield
```

## Rules (from PRD Section 14)
1. Only work on the current phase. Post gate summary and wait for "approved".
2. Ask before: new deps, tech changes, deploys, money-spending calls, file deletes, schema changes after Phase 0.
3. Never hardcode secrets. `.env` only. `sandbox/secrets.env` = obviously fake values only.
4. Phase 3: write fake-upstream tests BEFORE wiring real upstream.
5. After every task: app must still start. Run pytest + npm run build before each gate.
6. Be honest about bad metrics. Never fake eval numbers.
7. Small commits: one per task, e.g. `phase3: binary search paragraph attribution`.
8. Update this file at each gate.
9. If stuck >20 min on same error: stop and explain with 2 options.
10. No features outside the PRD. Ideas go in IDEAS.md.

## Key decisions
- Proxy: Python 3.11, FastAPI, httpx, pydantic v2, uv
- Upstream: Claude API via OpenAI-compat endpoint (`claude-haiku-5-5`)
- DB: Supabase (Postgres + Realtime)
- Dashboard: Next.js 14+ App Router, Tailwind, shadcn/ui, React Flow, Recharts
- Do NOT send temperature or seed to Claude models
