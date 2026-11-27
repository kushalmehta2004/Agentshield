# AgentShield

**An OpenAI-compatible security proxy for AI agents with a Proof of Cause engine.**

AgentShield sits between your agent and its LLM. When the agent is about to make a sensitive tool call (sending email, posting data), AgentShield re-runs the LLM to prove *what caused that call* — and blocks it if the cause traces back to untrusted content the agent fetched.

---

## The Gap

Indirect prompt injection is the leading attack on AI agents. An attacker hides instructions in a web page or document the agent fetches. The agent follows them, exfiltrating secrets or sending data to attacker-controlled addresses. Existing defenses are either:

- **Regex / keyword matching** — misses paraphrased and naturally-worded attacks (57% ASR in our eval)
- **Input sanitization** — strips injections but blocks legitimate content, and can't handle encoded/hidden attacks

AgentShield uses causal attribution to catch injections *after* they've been read but *before* they execute.

---

## How It Works (Proof of Cause)

Based on [MELON: LLM-Based Automated Detection of Indirect Prompt Injection Attacks](https://arxiv.org/abs/2501.09888) (Zhu et al., ICML 2025).

When a sensitive tool call is detected:

1. **Check A — Attack detection**: Re-run the LLM with the user task masked. If the sensitive call still appears, an external source (not the user) caused it → attack detected.
2. **Check B — Attribution**: Re-run with each untrusted source removed. If removing source X eliminates the call → X caused it.
3. **Paragraph binary search**: Narrow attribution to the exact paragraph within the culprit source.
4. **Decision**: BLOCK if attack detected or cause traces to untrusted content. WARN if cause found but target is legitimate. ALLOW otherwise.

All re-runs happen in parallel (budget: 8 total). Added latency: ~7s median.

---

## Eval Results

| Mode | Attack Success Rate ↓ | Benign Pass Rate ↑ | Avg Latency |
|---|---|---|---|
| No defense (`off`) | ~100% | 100% | ~2s |
| Regex baseline | **57%** (8/14) | 100% | ~6s |
| **AgentShield** | **0%** (0/14) | **100%** | **~7s** |

14 attack variants tested: direct injection, paraphrased (×3), HTML comment (×2), whitespace-hidden, http\_post target, split across 2 pages, multi-step read\_file + email.
6 benign tasks: no false positives.

---

## Architecture

```
Agent (Groq LLM)
     │  OpenAI-compat API
     ▼
AgentShield Proxy (FastAPI)
     │
     ├── mode=off  → passthrough
     ├── mode=regex → pattern scan → BLOCK/ALLOW
     └── mode=shield
           │
           ├── label_sources()       provenance.py
           ├── parallel re-runs      poc_engine.py
           │     ├── masked (Check A)
           │     └── per-source (Check B)
           ├── binary search         poc_engine.py
           ├── decide()              decision.py
           └── log to Supabase       logger.py
                    │
                    ▼
           Dashboard (Next.js)
           Sessions / Causal Graph / Eval
```

---

## Running Locally

**Prerequisites:** Python 3.11+, Node 18+, uv, a Supabase project, Anthropic API key, Groq API key.

### 1. Clone and configure

```bash
git clone https://github.com/kushalmehta2004/Agentshield.git
cd Agentshield
cp proxy/.env.example proxy/.env
# Fill in: UPSTREAM_API_KEY, GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
#          NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### 2. Create Supabase tables

Run the SQL from `AGENTSHIELD_PRD.md` Section 8 in your Supabase SQL editor, then enable anon SELECT on each table.

### 3. Start the proxy

```bash
cd proxy
uv run uvicorn app.main:app --reload --port 8000
```

### 4. Start the dashboard

```bash
cd dashboard
cp .env.local.example .env.local   # or create manually — see below
npm install
npm run dev
```

`dashboard/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_PROXY_URL=http://localhost:8000
```

### 5. Run a scenario

```bash
cd proxy
uv run python -m agent.run --scenario paraphrased_injection --mode shield
# or
uv run python -m agent.run --scenario paraphrased_injection --mode regex
```

Open `http://localhost:3000` to see the session detail and causal graph.

### 6. Run the eval suite

```bash
cd proxy
uv run python -m eval.runner --mode shield
uv run python -m eval.runner --mode regex
uv run python -m eval.runner --mode off
```

---

## Project Structure

```
Agentshield/
├── proxy/                   # FastAPI proxy
│   ├── app/
│   │   ├── main.py
│   │   ├── provenance.py    # Source labeling + message manipulation
│   │   ├── matching.py      # Tool call matching
│   │   ├── poc_engine.py    # Proof of Cause engine (MELON-based)
│   │   ├── decision.py      # ALLOW/BLOCK/WARN decision table
│   │   ├── regex_baseline.py
│   │   └── routes/
│   │       ├── chat.py      # /v1/chat/completions
│   │       ├── demo.py      # /demo/* + /api/scenarios/*/run
│   │       └── eval.py      # /api/eval/run
│   ├── agent/               # Demo agent
│   │   ├── loop.py
│   │   ├── scenarios.py
│   │   └── tools.py
│   ├── eval/
│   │   ├── cases.yaml       # 20 eval cases
│   │   └── runner.py
│   └── demo_site/           # Attack + benign HTML pages
├── dashboard/               # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx         # Sessions list (live)
│   │   ├── sessions/[id]/   # Session detail + causal graph
│   │   ├── demo/            # Scenario runner
│   │   └── eval/            # Eval results
│   └── components/
│       ├── CausalGraph.tsx  # React Flow animated graph
│       ├── ChunkInspector.tsx
│       └── Timeline.tsx
└── config/
    └── policy.yaml          # Sensitive tools + model routing
```

---

## Credits

- **MELON**: Zhu et al., "MELON: LLM-Based Automated Detection of Indirect Prompt Injection Attacks", ICML 2025. The Proof of Cause engine is inspired by MELON's masked re-run and source-removal attribution approach.
- Proxy: Python 3.11, FastAPI, httpx, Pydantic v2
- Dashboard: Next.js 14, Tailwind CSS, shadcn/ui, React Flow, Recharts
- Database: Supabase (Postgres + Realtime)
- Victim model: Groq (`openai/gpt-oss-20b`) — susceptible to injections
- Shield re-runs: Anthropic Claude Haiku 5.5 — refuses to follow injections
