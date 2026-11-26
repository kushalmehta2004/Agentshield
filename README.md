# AgentShield

**AgentShield is a security proxy for AI agents that doesn't just block suspicious tool calls — it *proves* which piece of untrusted content caused them.**

> *"Other agent firewalls block what looks bad. AgentShield proves what made your agent go rogue."*

## What it does

AI agents read untrusted content (webpages, emails, files). Attackers hide instructions in that content (indirect prompt injection) and hijack the agent. AgentShield's **Proof of Cause engine** re-runs the LLM decision under controlled changes to identify and prove exactly which chunk of untrusted content triggered the sensitive action — then blocks it.

## Architecture

```
Demo Agent → AgentShield Proxy (FastAPI) → Upstream LLM (Claude)
                      ↓
                  Supabase (Postgres + Realtime)
                      ↓
              Dashboard (Next.js + React Flow)
```

## Running locally

```bash
# Proxy
cd proxy
uv sync
cp ../.env.example ../.env   # fill in keys
uv run uvicorn app.main:app --reload

# Dashboard
cd dashboard
npm install
npm run dev

# Agent
cd proxy
uv run python -m agent.run --scenario benign_summary_email --mode shield
```

## Eval results

_To be filled after Phase 5._

## References

- MELON: Zhu et al., ICML 2025. arXiv:2502.05174
- OWASP LLM01: Prompt Injection
