"""CLI entry point.

Usage:
    python -m agent.run --scenario benign_summary_email --mode shield
    python -m agent.run --scenario paraphrased_injection --mode off
"""
import argparse
import sys
import uuid
from pathlib import Path

# Load .env from repo root
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from agent.scenarios import SCENARIOS
from agent.loop import run_scenario


def main():
    parser = argparse.ArgumentParser(description="AgentShield demo agent")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS.keys()))
    parser.add_argument("--mode", default="shield", choices=["off", "regex", "shield"])
    parser.add_argument("--session", default=None, help="Session ID (auto-generated if omitted)")
    args = parser.parse_args()

    session_id = args.session or str(uuid.uuid4())
    run_scenario(args.scenario, args.mode, session_id)


if __name__ == "__main__":
    main()
