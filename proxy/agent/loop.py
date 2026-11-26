"""Standard tool-calling agent loop.

Calls the AgentShield proxy (which forwards to Claude).
Prints each step with rich formatting.
"""
import json
import os
import sys
from pathlib import Path

from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from agent.tools import TOOL_SCHEMAS, dispatch

console = Console()

PROXY_URL = os.getenv("PROXY_PUBLIC_URL", "http://localhost:8000")
AGENT_MODEL = os.getenv("AGENT_MODEL", os.getenv("UPSTREAM_MODEL", "claude-haiku-5-5"))
MAX_STEPS = 8


def run_scenario(scenario_name: str, mode: str, session_id: str) -> None:
    from agent.scenarios import SCENARIOS
    scenario = SCENARIOS[scenario_name]

    client = OpenAI(
        base_url=f"{PROXY_URL}/v1",
        api_key=os.getenv("UPSTREAM_API_KEY", "x"),
    )

    extra_headers = {
        "X-AgentShield-Session": session_id,
        "X-AgentShield-Mode": mode,
        "X-AgentShield-Scenario": scenario_name,
    }

    messages = [
        {"role": "system", "content": scenario["system"]},
        {"role": "user", "content": scenario["user"]},
    ]

    console.print(Panel(
        f"[bold cyan]Scenario:[/] {scenario_name}  [bold cyan]Mode:[/] {mode}  [bold cyan]Session:[/] {session_id}",
        title="AgentShield Demo Agent",
    ))
    console.print(f"[bold green]User:[/] {scenario['user']}\n")

    for step in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            extra_headers=extra_headers,
            max_tokens=1024,
        )

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if msg.content:
            console.print(f"[bold yellow]Step {step + 1} — Assistant:[/] {msg.content}")

        if not msg.tool_calls:
            console.print("[bold green]✓ Done[/]")
            break

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}

            console.print(f"[bold magenta]Step {step + 1} — Tool call:[/] {name}({args})")

            result = dispatch(name, args, session_id)
            console.print(f"[dim]  → {result[:200]}{'...' if len(result) > 200 else ''}[/]")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        console.print("[bold red]⚠ Max steps reached[/]")
