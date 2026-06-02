#!/usr/bin/env python3

import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_CONFIG_PATH = ROOT / "example.config.json"
ENV_PATH = ROOT / ".env"
REQUIRED_DIRS = [
    ROOT / "jobs",
    ROOT / "output",
    ROOT / "pipelines",
    ROOT / "Prompt Logs",
]
PLACEHOLDER_WATCH_FOLDER = "SET_THIS_TO_THE_FOLDER_YOU_WANT_THE_WATCHER_TO_MONITOR"


def resolve_watch_dir(raw_value: str) -> Path:
    raw = (raw_value or "").strip()
    if not raw:
        raise ValueError("watched_folder is blank")
    if raw == "/watch":
        return ROOT / "watch"
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else (ROOT / candidate).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or repair the local config and folder structure.")
    parser.add_argument("--fix", action="store_true", help="Create missing files and directories where safe.")
    args = parser.parse_args()

    problems: list[str] = []

    if not CONFIG_PATH.exists():
        if args.fix and EXAMPLE_CONFIG_PATH.exists():
            shutil.copy2(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
            print("Created config.json from example.config.json")
        else:
            problems.append("config.json is missing")

    if not CONFIG_PATH.exists():
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    try:
        config = json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: config.json is not valid JSON: {exc}")
        return 1

    if not isinstance(config, dict):
        print("ERROR: config.json must contain a JSON object")
        return 1

    required_keys = [
        "default_pipeline_id",
        "watched_folder",
        "text_model",
        "image_model",
        "aspect_ratio",
        "run_count",
        "variety_compression_prompt",
    ]
    for key in required_keys:
        if key not in config:
            problems.append(f"config.json is missing required key: {key}")

    watched_folder_value = str(config.get("watched_folder") or "").strip()
    if not watched_folder_value or watched_folder_value == PLACEHOLDER_WATCH_FOLDER:
        problems.append("config.json watched_folder must be set to a real folder path")
        watch_dir = None
    else:
        try:
            watch_dir = resolve_watch_dir(watched_folder_value)
        except ValueError as exc:
            problems.append(str(exc))
            watch_dir = None

    if watch_dir is not None:
        REQUIRED_DIRS_WITH_WATCH = REQUIRED_DIRS + [watch_dir]
    else:
        REQUIRED_DIRS_WITH_WATCH = list(REQUIRED_DIRS)

    for path in REQUIRED_DIRS_WITH_WATCH:
        if path.exists():
            if not path.is_dir():
                problems.append(f"Required path exists but is not a directory: {path}")
            continue
        if args.fix:
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {path}")
        else:
            problems.append(f"Missing directory: {path}")

    if not ENV_PATH.exists():
        if args.fix:
            ENV_PATH.write_text(
                "OPENROUTER_API_KEY=\n"
                "REPLICATE_API_TOKEN=\n"
            )
            print("Created blank .env file")
        else:
            problems.append(".env is missing")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print("Config check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
