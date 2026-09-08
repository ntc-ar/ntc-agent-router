"""Local CLI for setup and the same worker operations exposed over MCP."""

import argparse
import getpass
import json
from pathlib import Path
import sys

from . import jobs
from .credentials import save_key
from .openrouter_client import OpenRouterError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("credential", "status", "models", "refresh-models"):
        command = commands.add_parser(name)
        if name in ("status", "models"):
            command.add_argument("--workspace", default="")
    for name in ("worker", "result", "cancel"):
        sub = commands.add_parser(name)
        sub.add_argument("task_id")
    start = commands.add_parser("start")
    start.add_argument("--model", required=True)
    start.add_argument("--task-file", type=Path, required=True)
    start.add_argument("--workspace", default="")
    start.add_argument("--context-file", action="append", default=[])
    start.add_argument("--max-tokens", type=int)
    start.add_argument("--effort")
    args = parser.parse_args()
    try:
        if args.command == "credential":
            save_key(getpass.getpass("OpenRouter API key (stored in OS credential store): ").strip())
            result = {"credential_saved": True}
        elif args.command == "worker":
            jobs.run_worker(args.task_id)
            return 0
        elif args.command == "start":
            result = jobs.start_task(args.task_file.read_text(encoding="utf-8"), args.model,
                                     args.workspace, args.context_file, args.max_tokens, args.effort)
        elif args.command == "result":
            result = jobs.read_task(args.task_id)
        elif args.command == "cancel":
            result = jobs.cancel_task(args.task_id)
        else:
            result = {"status": jobs.status, "models": jobs.models,
                      "refresh-models": jobs.refresh_models}[args.command](
                          **({"workspace": args.workspace} if args.command in ("status", "models") else {}))
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, OpenRouterError) as error:
        # Never print tracebacks or OS error paths which might include task inputs.
        message = str(error) if isinstance(error, (ValueError, OpenRouterError)) else "Local file operation failed."
        print(json.dumps({"error": message, "code": getattr(error, "code", "local_error")}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
