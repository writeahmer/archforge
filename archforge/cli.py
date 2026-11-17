"""
Command-Line Interface for ArchForge.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from archforge.agent.events import EventBus, EventType
from archforge.agent.generator import ProjectGenerator
from archforge.config import AgentConfig


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ArchForge: Autonomous Architectural Code Agent powered by DeepSeek."
    )
    parser.add_argument(
        "--doc",
        type=str,
        default="samples/Architecture_Documentation.md",
        help="Path to Architecture_Documentation.md",
    )
    parser.add_argument(
        "--views",
        type=str,
        default="samples/Architecture_View.md",
        help="Path to Architecture_View.md",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="generated_project",
        help="Target directory for generated software project",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="DeepSeek API Key (overrides DEEPSEEK_API_KEY environment variable)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="DeepSeek Model identifier (default: deepseek-chat / deepseek-v4-pro)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="",
        help="Base URL for DeepSeek API",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force offline mock LLM mode for local testing without API key",
    )

    args = parser.parse_args()

    cfg = AgentConfig.load()
    if args.api_key:
        cfg.api_key = args.api_key
    if args.model:
        cfg.model = args.model
    if args.base_url:
        cfg.base_url = args.base_url

    doc_file = Path(args.doc).resolve()
    views_file = Path(args.views).resolve()
    out_dir = Path(args.out).resolve()

    if not doc_file.exists():
        print(f"Error: Architecture doc file not found at: {doc_file}", file=sys.stderr)
        return 1
    if not views_file.exists():
        print(f"Error: Architecture views file not found at: {views_file}", file=sys.stderr)
        return 1

    print("=====================================================")
    print("                ARCHFORGE CODE AGENT                 ")
    print("=====================================================")
    print(f"Doc Input:   {doc_file}")
    print(f"Views Input: {views_file}")
    print(f"Output Dir:  {out_dir}")
    print(f"Model:       {cfg.model}")
    print(f"Base URL:    {cfg.base_url}")
    print(f"API Key:     {cfg.get_masked_api_key() or '(None provided - will use mock generator)'}")
    print("=====================================================\n")

    event_bus = EventBus()

    def console_listener(evt):
        if evt.event_type == EventType.STATUS:
            print(f"[STATUS] {evt.message}")
        elif evt.event_type == EventType.PLAN:
            print("[PLAN UPDATE]:")
            for t in evt.data.get("todos", []):
                mark = "[x]" if t.get("status") == "completed" else "[-]" if t.get("status") == "in_progress" else "[ ]"
                print(f"  {mark} {t.get('task')}")
        elif evt.event_type == EventType.TOOL_CALL:
            print(f"  -> Tool Call: {evt.data.get('tool')}")
        elif evt.event_type == EventType.WARNING:
            print(f"[WARN] {evt.message}")
        elif evt.event_type == EventType.ERROR:
            print(f"[ERROR] {evt.message}", file=sys.stderr)
        elif evt.event_type == EventType.DONE:
            print(f"\n[DONE] {evt.message}")

    event_bus.subscribe(console_listener)

    generator = ProjectGenerator(
        doc_path=doc_file,
        views_path=views_file,
        output_dir=out_dir,
        config=cfg,
        event_bus=event_bus,
    )

    result = generator.run(mock_llm=args.mock)
    if result.get("success"):
        print("\nProject generation succeeded!")
        print(f"Artifacts located at: {out_dir}")
        return 0
    else:
        print("\nProject generation failed or was cancelled.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
