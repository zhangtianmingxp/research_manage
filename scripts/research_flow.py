#!/usr/bin/env python3
"""Helper commands for the interactive research workflow template."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".research_agent"
ANS_DIR = ROOT / "ans_qes"
PROGRESS_PATH = AGENT_DIR / "progress.json"
STATE_PATH = AGENT_DIR / "project_state.md"
PROMPT_TEMPLATE = AGENT_DIR / "templates" / "prompt_template.md"
COMMIT_TEMPLATE = AGENT_DIR / "templates" / "commit_template.md"


PROMPT_RE = re.compile(r"^prompt(\d+)\.md$")
RESULT_RE = re.compile(r"^result(\d+)\.md$")


def load_progress() -> dict:
    if not PROGRESS_PATH.exists():
        return {}
    return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def numbered_files(pattern: re.Pattern[str]) -> dict[int, Path]:
    if not ANS_DIR.exists():
        return {}
    items: dict[int, Path] = {}
    for path in ANS_DIR.iterdir():
        match = pattern.match(path.name)
        if match:
            items[int(match.group(1))] = path
    return items


def next_id() -> int:
    prompts = numbered_files(PROMPT_RE)
    results = numbered_files(RESULT_RE)
    used = set(prompts) | set(results)
    n = 1
    while n in used:
        n += 1
    return n


def required_paths() -> list[Path]:
    return [
        ROOT / "AGENTS.md",
        ROOT / "PROJECT_RULES.md",
        ROOT / "project_plan.md",
        ROOT / "README.md",
        ANS_DIR / "README.md",
        AGENT_DIR / "AGENTS.md",
        AGENT_DIR / "config.yaml",
        STATE_PATH,
        PROGRESS_PATH,
        AGENT_DIR / "templates" / "prompt_template.md",
        AGENT_DIR / "templates" / "result_template.md",
        AGENT_DIR / "templates" / "commit_template.md",
        ROOT / "scripts" / "research_flow.py",
    ]


def cmd_status(_: argparse.Namespace) -> int:
    progress = load_progress()
    print(f"current_round: {progress.get('current_round', 0)}")
    print(f"phase: {progress.get('phase', 'idle')}")
    print(f"last_prompt: {progress.get('last_prompt')}")
    print(f"last_result: {progress.get('last_result')}")
    print(f"last_commit: {progress.get('last_commit')}")
    print(f"auto_next: {progress.get('auto_next', False)}")
    issues = progress.get("open_issues", [])
    if issues:
        print("open_issues:")
        for issue in issues:
            print(f"- {issue}")
    return 0


def cmd_next_id(_: argparse.Namespace) -> int:
    print(next_id())
    return 0


def check_pairs() -> list[str]:
    problems: list[str] = []
    prompts = numbered_files(PROMPT_RE)
    results = numbered_files(RESULT_RE)

    for n in sorted(results):
        if n not in prompts:
            problems.append(f"result{n}.md exists without prompt{n}.md")

    prompt_numbers = sorted(prompts)
    if prompt_numbers:
        expected = list(range(1, max(prompt_numbers) + 1))
        missing = sorted(set(expected) - set(prompt_numbers))
        for n in missing:
            problems.append(f"missing prompt{n}.md")

    return problems


def cmd_check(_: argparse.Namespace) -> int:
    problems: list[str] = []

    for path in required_paths():
        if not path.exists():
            problems.append(f"missing required path: {path.relative_to(ROOT)}")

    progress = load_progress()
    for key in ("auto_next", "auto_execute_prompt", "auto_commit", "auto_push"):
        if progress.get(key) is not False:
            problems.append(f"progress.json must set {key}: false")

    problems.extend(check_pairs())

    if problems:
        print("check: failed")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("check: ok")
    print(f"next_prompt_id: {next_id()}")
    return 0


def render_template(path: Path, values: dict[str, str | int]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def update_state_for_prompt(round_id: int, prompt_path: Path) -> None:
    progress = load_progress()
    progress.update(
        {
            "current_round": round_id,
            "phase": "prompt_drafted",
            "last_prompt": str(prompt_path.relative_to(ROOT)).replace("\\", "/"),
            "auto_next": False,
            "auto_execute_prompt": False,
            "auto_commit": False,
            "auto_push": False,
        }
    )
    save_progress(progress)

    state = (
        "# Project State\n\n"
        "## Current Status\n\n"
        f"- current_round: {round_id}\n"
        "- phase: prompt_drafted\n"
        f"- last_prompt: {prompt_path.relative_to(ROOT).as_posix()}\n"
        f"- last_result: {progress.get('last_result')}\n"
        f"- last_commit: {progress.get('last_commit')}\n"
        "- auto_next: false\n\n"
        "## Open Issues\n\n"
        "- prompt 已生成，等待用户审查；不得自动执行。\n\n"
        "## Notes\n\n"
        "- 用户确认执行后，才允许读取该 prompt 并生成对应 result。\n"
        "- 本轮结束后必须停止，等待用户下一条明确指令。\n"
    )
    STATE_PATH.write_text(state, encoding="utf-8")


def cmd_init_round(args: argparse.Namespace) -> int:
    round_id = args.round if args.round is not None else next_id()
    prompt_path = ANS_DIR / f"prompt{round_id}.md"

    if prompt_path.exists() and not args.force:
        print(f"refusing to overwrite existing {prompt_path.relative_to(ROOT)}")
        print("use --force only if the user explicitly asked to overwrite it")
        return 1

    text = render_template(
        PROMPT_TEMPLATE,
        {
            "round": round_id,
            "title": args.title,
        },
    )
    prompt_path.write_text(text, encoding="utf-8")
    update_state_for_prompt(round_id, prompt_path)
    print(f"created: {prompt_path.relative_to(ROOT)}")
    print("status: prompt_drafted; stop and wait for user review")
    return 0


def summarize_prompt(round_id: int) -> str:
    prompt_path = ANS_DIR / f"prompt{round_id}.md"
    if not prompt_path.exists():
        return f"round {round_id}"

    for line in prompt_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped != "{title}":
            return stripped[:60]
    return f"round {round_id}"


def cmd_suggest_commit(args: argparse.Namespace) -> int:
    round_id = args.round
    summary = args.summary or summarize_prompt(round_id)
    summary = re.sub(r"\s+", " ", summary).strip()
    message = render_template(
        COMMIT_TEMPLATE,
        {
            "round": round_id,
            "summary": summary,
        },
    ).strip()
    print(message)
    print("suggestion only; commit requires explicit user confirmation")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interactive research workflow helper. It never calls LLM APIs, commits, pushes, or advances rounds automatically."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show current workflow status")
    status.set_defaults(func=cmd_status)

    next_id_parser = subparsers.add_parser("next-id", help="print next available prompt/result id")
    next_id_parser.set_defaults(func=cmd_next_id)

    check = subparsers.add_parser("check", help="check required structure and numbering")
    check.set_defaults(func=cmd_check)

    init_round = subparsers.add_parser("init-round", help="create a prompt draft and stop")
    init_round.add_argument("--round", type=int, default=None, help="round number; defaults to next available id")
    init_round.add_argument("--title", required=True, help="prompt title")
    init_round.add_argument("--force", action="store_true", help="overwrite existing prompt")
    init_round.set_defaults(func=cmd_init_round)

    suggest = subparsers.add_parser("suggest-commit", help="suggest a commit message for a round")
    suggest.add_argument("--round", type=int, required=True, help="round number")
    suggest.add_argument("--summary", default=None, help="explicit commit summary")
    suggest.set_defaults(func=cmd_suggest_commit)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
