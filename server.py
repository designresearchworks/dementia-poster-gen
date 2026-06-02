"""
Dementia Design Poster Generator
FastAPI backend: watches a folder for images, interprets them via Claude (OpenRouter),
generates product posters via Nano Banana 2 (Replicate).
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
from starlette.background import BackgroundTask

load_dotenv()


class SuppressNoisyAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        config_path = Path(__file__).parent / "config.json"
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                if isinstance(config, dict) and bool(config.get("http_access_logging", False)):
                    return True
            return False
        except Exception:
            return False


logging.getLogger("uvicorn.access").addFilter(SuppressNoisyAccessFilter())
terminal_logger = logging.getLogger("uvicorn.error")
terminal_logger.setLevel(logging.INFO)
TERMINAL_LOG_SOURCES = {"Watch Folder", "Jobs", "Processing", "System"}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

DEFAULT_WATCH_DIR = Path(__file__).parent / "watch"
OUTPUT_DIR = Path(__file__).parent / "output"
PIPELINES_DIR = Path(__file__).parent / "pipelines"
PROMPT_LOGS_DIR = Path(__file__).parent / "Prompt Logs"
JOBS_DIR = Path(__file__).parent / "jobs"
CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_WATCH_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PIPELINES_DIR.mkdir(exist_ok=True)
PROMPT_LOGS_DIR.mkdir(exist_ok=True)
JOBS_DIR.mkdir(exist_ok=True)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
EXTRACTED_CONCEPTS_TOKEN = "{extracted-concepts}"
MEANINGFUL_DIFFERENCE_TOKEN = "{meaningfuldifference}"
EXTRACTED_CONCEPTS_PROMPT = (
    "Look at these source images and extract the key concepts, themes, activities, emotions, and needs they contain. "
    "Return only a concise comma-separated list of extracted concepts. If you can see conceptual connections between the concepts, then explain why and how they are connected. No markdown, no bullets, no explanation."
)
DEFAULT_VARIETY_COMPRESSION_PROMPT = (
    "You will be given earlier interpretations from a design ideation run. Create a list of product names, "
    "technologies, features, and contexts that have been included in these earlier interpretations. Capture the "
    "shape of the idea. Do not create any markdown or headers. Just output a simple list of features and technologies. "
    "The list need not be exhaustive, but should include from 10-30 items that capture the spirit of the previous "
    "interpretations best.\n\n"
    "<previousinterpretations>\n{previous_interpretations}\n</previousinterpretations>"
)
TEXT_MODELS = {
    "anthropic/claude-opus-4.8-fast": {
        "label": "Claude Opus 4.8 Fast",
        "model": "anthropic/claude-opus-4.8-fast",
    },
    "anthropic/claude-opus-4.8": {
        "label": "Claude Opus 4.8",
        "model": "anthropic/claude-opus-4.8",
    },
    "anthropic/claude-opus-4.6": {
        "label": "Claude Opus 4.6",
        "model": "anthropic/claude-opus-4.6",
    },
    "anthropic/claude-opus-4.6:reasoning": {
        "label": "Claude Opus 4.6 (Reasoning)",
        "model": "anthropic/claude-opus-4.6",
        "reasoning": {"enabled": True},
    },
    "anthropic/claude-sonnet-4.6": {
        "label": "Claude Sonnet 4.6",
        "model": "anthropic/claude-sonnet-4.6",
    },
    "anthropic/claude-sonnet-4.6:reasoning": {
        "label": "Claude Sonnet 4.6 (Reasoning)",
        "model": "anthropic/claude-sonnet-4.6",
        "reasoning": {"enabled": True},
    },
    "anthropic/claude-haiku-4.5": {
        "label": "Claude Haiku 4.5",
        "model": "anthropic/claude-haiku-4.5",
    },
    "google/gemini-3.5-flash": {
        "label": "Gemini 3.5 Flash",
        "model": "google/gemini-3.5-flash",
    },
    "google/gemini-2.5-flash": {
        "label": "Gemini 2.5 Flash",
        "model": "google/gemini-2.5-flash",
    },
    "google/gemini-3.1-pro-preview": {
        "label": "Gemini 3.1 Pro Preview",
        "model": "google/gemini-3.1-pro-preview",
    },
}
IMAGE_MODELS = {
    "replicate:google/nano-banana-pro": {
        "label": "Nano Banana Pro (Replicate)",
        "provider": "replicate",
        "model": "google/nano-banana-pro",
    },
    "replicate:google/imagen-4-ultra": {
        "label": "Imagen 4 Ultra (Replicate)",
        "provider": "replicate",
        "model": "google/imagen-4-ultra",
    },
    "replicate:google/nano-banana": {
        "label": "Nano Banana (Replicate)",
        "provider": "replicate",
        "model": "google/nano-banana",
    },
    "replicate:google/nano-banana-2": {
        "label": "Nano Banana 2 (Replicate)",
        "provider": "replicate",
        "model": "google/nano-banana-2",
    },
    "replicate:black-forest-labs/flux-2-pro": {
        "label": "FLUX.2 Pro (Replicate)",
        "provider": "replicate",
        "model": "black-forest-labs/flux-2-pro",
    },
    "replicate:openai/gpt-image-1.5": {
        "label": "GPT Image 1.5 (Replicate)",
        "provider": "replicate",
        "model": "openai/gpt-image-1.5",
    },
    "replicate:openai/gpt-image-2": {
        "label": "GPT Image 2.0 (Replicate)",
        "provider": "replicate",
        "model": "openai/gpt-image-2",
    },
    "openrouter:google/gemini-3.1-flash-image-preview": {
        "label": "Gemini 3.1 Flash Image Preview (OpenRouter)",
        "provider": "openrouter",
        "model": "google/gemini-3.1-flash-image-preview",
    },
}
ASPECT_RATIOS = {"1:1", "3:2", "2:3", "3:4", "4:3", "9:16", "16:9"}
MODEL_ASPECT_RATIOS = {
    "replicate:openai/gpt-image-1.5": {"1:1", "3:2", "2:3"},
    "replicate:openai/gpt-image-2": {"1:1", "3:2", "2:3"},
}
PRINT_ORIENTATIONS = {
    "portrait": {
        "label": "Portrait",
        "lp_options": [],
    },
    "landscape": {
        "label": "Landscape",
        "lp_options": ["-o", "orientation-requested=4"],
    },
}
PRINT_FIT_MODES = {
    "default": {
        "label": "Printer Default",
        "lp_options": [],
    },
    "fit": {
        "label": "Fit To Page",
        "lp_options": ["-o", "fit-to-page"],
    },
    "actual": {
        "label": "Actual Size",
        "lp_options": ["-o", "scaling=100"],
    },
}

# --- Default prompts ---

DEFAULT_INTERPRETATION_PROMPT = (
    "You are a design researcher working on products for people living with dementia. "
    "Examine these images carefully. They contain handwritten notes, sketches, and ideas "
    "from a co-design workshop with carers, clinicians, and people with lived experience of dementia. "
    "Based on what you see across all of the images, describe a single product concept that responds "
    "to the needs and ideas expressed. Your description must be between 3 and 6 sentences — one clear "
    "paragraph. Focus on what the product does, who it helps, and why it matters."
)

DEFAULT_IMAGE_PROMPT = (
    "Create a professional product poster for the following product designed for people with dementia:\n\n"
    "{description}\n\n"
    "The poster should be warm, inviting, and clearly communicate the product's purpose. "
    "Use a clean layout with readable text, soft but confident colours, and imagery that feels "
    "respectful and empowering — not clinical or patronising. Suitable for printing at A3 size. "
    "Aspect ratio 3:4. Resolution 2K."
)
def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "pipeline"


def pipeline_path(pipeline_id: str) -> Path:
    safe_id = slugify(pipeline_id)
    return PIPELINES_DIR / f"{safe_id}.md"


def resolve_pipeline_path(pipeline_id: str) -> Path:
    for path in PIPELINES_DIR.glob("*.md"):
        if path.stem == pipeline_id:
            return path
    fallback = pipeline_path(pipeline_id)
    if fallback.exists():
        return fallback
    raise HTTPException(404, f"Pipeline not found: {pipeline_id}")


def parse_pipeline_markdown(content: str, pipeline_id: str) -> dict:
    lines = content.splitlines()
    name = pipeline_id.replace("-", " ").title()
    interpretation_lines = []
    image_lines = []
    current_section = None

    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                name = title
            continue
        if line.strip() == "## Interpretation Prompt":
            current_section = "interpretation"
            continue
        if line.strip() == "## Image Generation Prompt":
            current_section = "image"
            continue

        if current_section == "interpretation":
            interpretation_lines.append(line)
        elif current_section == "image":
            image_lines.append(line)

    interpretation = "\n".join(interpretation_lines).strip()
    image = "\n".join(image_lines).strip()
    if not interpretation or not image:
        raise HTTPException(500, f"Pipeline file is invalid: {pipeline_id}")

    return {
        "id": pipeline_id,
        "name": name,
        "interpretation": interpretation,
        "image": image,
        "path": str(resolve_pipeline_path(pipeline_id)) if PIPELINES_DIR.exists() else str(pipeline_path(pipeline_id)),
    }


def render_pipeline_markdown(name: str, interpretation: str, image: str) -> str:
    return (
        f"# {name.strip()}\n\n"
        "## Interpretation Prompt\n\n"
        f"{interpretation.strip()}\n\n"
        "## Image Generation Prompt\n\n"
        f"{image.strip()}\n"
    )


def build_pipeline_boilerplate(name: str) -> str:
    safe_name = (name or "New Pipeline").strip() or "New Pipeline"
    return render_pipeline_markdown(
        safe_name,
        "Describe what should be interpreted from the selected source images. Explain the context, output style, and any constraints for the descriptive response.",
        "Create an image based on the following description:\n\n{description}\n\nExplain the visual style, layout, and purpose of the final image.",
    )


def ensure_default_pipeline() -> str:
    viable_ids = list_viable_pipeline_ids()
    if viable_ids:
        return viable_ids[0]

    default_id = "product-poster"
    content = render_pipeline_markdown(
        "Product Poster",
        DEFAULT_INTERPRETATION_PROMPT,
        DEFAULT_IMAGE_PROMPT,
    )
    pipeline_path(default_id).write_text(content)
    return default_id


def list_viable_pipeline_ids() -> list[str]:
    viable_ids = []
    for path in sorted(PIPELINES_DIR.glob("*.md")):
        try:
            parse_pipeline_markdown(path.read_text(), path.stem)
        except HTTPException:
            continue
        viable_ids.append(path.stem)
    return viable_ids


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_fallback_pipeline_id() -> str:
    viable_ids = list_viable_pipeline_ids()
    if not viable_ids:
        return ensure_default_pipeline()
    return "product-poster" if "product-poster" in viable_ids else viable_ids[0]


def build_default_config(fallback_pipeline_id: str) -> dict:
    default_pipeline_id = "blueprint" if "blueprint" in list_viable_pipeline_ids() else fallback_pipeline_id
    return {
        "default_pipeline_id": default_pipeline_id,
        "debug_mode": False,
        "skip_image_generation": False,
        "watcher_enabled": True,
        "watched_folder": "watch/",
        "text_model": "anthropic/claude-opus-4.6",
        "image_model": "replicate:google/nano-banana-2",
        "aspect_ratio": "1:1",
        "run_count": 4,
        "http_access_logging": False,
        "printer_name": "Brother_HL_L3240CDW_series",
        "send_to_printer": False,
        "print_orientation": "portrait",
        "print_fit_mode": "default",
        "encourage_variety_within_batches": True,
        "encourage_variety_across_session": False,
        "variety_compression_prompt": (
            "You will be given earlier interpretations of an idea. Create a list of the key ideas that were in the "
            "earlier interpretations, no more than 5-10 ideas in the list, choose words that capture the spirit of "
            "the previous interpretations best. Output without any markdown or headers \n\n<previousinterpretations>\n"
            "{previous_interpretations}\n</previousinterpretations>"
        ),
        "layout": {
            "content_row_height": 585,
        },
    }


def get_default_config_template() -> dict:
    return build_default_config(get_fallback_pipeline_id())


def ensure_config() -> dict:
    fallback_pipeline_id = get_fallback_pipeline_id()
    if not CONFIG_FILE.exists():
        default_config = build_default_config(fallback_pipeline_id)
        save_config(default_config)
        existing = dict(default_config)
    else:
        existing = load_config()
    if "variety_compression_prompt" not in existing:
        raise RuntimeError("config.json is missing required setting: variety_compression_prompt")
    if not isinstance(existing.get("variety_compression_prompt"), str) or not str(existing.get("variety_compression_prompt")).strip():
        raise RuntimeError("config.json setting variety_compression_prompt must be a non-empty string")
    existing_layout = existing.get("layout") or {}
    normalized_image_model = (
        existing.get("image_model")
        if existing.get("image_model") in IMAGE_MODELS
        else "replicate:google/nano-banana-pro"
    )
    allowed_default_aspect_ratios = get_allowed_aspect_ratios(normalized_image_model)
    normalized_aspect_ratio = str(existing.get("aspect_ratio") or "3:4")
    if normalized_aspect_ratio not in allowed_default_aspect_ratios:
        normalized_aspect_ratio = "3:4" if "3:4" in allowed_default_aspect_ratios else sorted(allowed_default_aspect_ratios)[0]
    normalized_run_count = existing.get("run_count", 1)
    if not isinstance(normalized_run_count, int):
        try:
            normalized_run_count = int(normalized_run_count)
        except Exception:
            normalized_run_count = 1
    normalized_run_count = max(1, min(20, normalized_run_count))
    normalized_printer = str(existing.get("printer_name") or "").strip()
    normalized_send_to_printer = bool(existing.get("send_to_printer", False))
    normalized_print_orientation = (
        existing.get("print_orientation")
        if existing.get("print_orientation") in PRINT_ORIENTATIONS
        else "portrait"
    )
    normalized_print_fit_mode = (
        existing.get("print_fit_mode")
        if existing.get("print_fit_mode") in PRINT_FIT_MODES
        else "default"
    )
    normalized = {
        "default_pipeline_id": existing.get("default_pipeline_id")
        if existing.get("default_pipeline_id") in list_viable_pipeline_ids()
        else fallback_pipeline_id,
        "debug_mode": bool(existing.get("debug_mode", False)),
        "skip_image_generation": bool(existing.get("skip_image_generation", False)),
        "watcher_enabled": bool(existing.get("watcher_enabled", True)),
        "watched_folder": str(existing.get("watched_folder") or "watch/").strip() or "watch/",
        "text_model": existing.get("text_model")
        if existing.get("text_model") in TEXT_MODELS
        else "anthropic/claude-opus-4.6",
        "image_model": normalized_image_model,
        "aspect_ratio": normalized_aspect_ratio,
        "run_count": normalized_run_count,
        "http_access_logging": bool(existing.get("http_access_logging", False)),
        "printer_name": normalized_printer,
        "send_to_printer": normalized_send_to_printer,
        "print_orientation": normalized_print_orientation,
        "print_fit_mode": normalized_print_fit_mode,
        "encourage_variety_within_batches": bool(existing.get("encourage_variety_within_batches", False)),
        "encourage_variety_across_session": bool(existing.get("encourage_variety_across_session", False)),
        "variety_compression_prompt": str(existing.get("variety_compression_prompt")).strip(),
        "layout": {
            "content_row_height": int(existing_layout.get("content_row_height", 448))
            if isinstance(existing_layout.get("content_row_height", 448), (int, float))
            else 448,
        },
    }

    normalized["layout"]["content_row_height"] = max(220, min(1200, normalized["layout"]["content_row_height"]))

    if existing != normalized or not CONFIG_FILE.exists():
        save_config(normalized)

    return normalized


def serialize_config_json(config: dict) -> str:
    return json.dumps(config, indent=2, ensure_ascii=False)


def get_raw_config_content() -> str:
    if not CONFIG_FILE.exists():
        return serialize_config_json(get_default_config_template())
    return CONFIG_FILE.read_text()


async def apply_config_runtime_updates(previous_encourage_variety_across_session: Optional[bool] = None):
    global current_pipeline_id, current_pipeline
    current_pipeline_id = get_default_pipeline_id()
    current_pipeline = load_pipeline(current_pipeline_id)
    pipeline_state["pipeline_id"] = current_pipeline_id
    pipeline_state["image_model"] = get_default_image_model()
    pipeline_state["aspect_ratio"] = get_default_aspect_ratio()
    pipeline_state["send_to_printer"] = get_send_to_printer()
    pipeline_state["run_count"] = get_default_run_count()
    pipeline_state["encourage_variety_within_batches"] = get_encourage_variety_within_batches()
    pipeline_state["encourage_variety_across_session"] = get_encourage_variety_across_session()
    if (
        previous_encourage_variety_across_session is not None
        and get_encourage_variety_across_session()
        and not previous_encourage_variety_across_session
    ):
        clear_session_variety_state()
        log_event("info", "System", "Session variety memory reset because across-session variety was enabled")
    await sync_watcher_state(
        f"Configuration applied for watched folder {resolve_watched_folder_path()}",
        force_restart=True,
    )


runtime_errors: list[dict] = []
system_events: list[dict] = []
MAX_SYSTEM_EVENTS = 400


def log_event(level: str, source: str, message: str, **metadata):
    event = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "source": source,
        "message": message,
        "metadata": {key: value for key, value in metadata.items() if value is not None},
    }
    system_events.append(event)
    del system_events[:-MAX_SYSTEM_EVENTS]

    if level == "error":
        runtime_errors.append({
            "timestamp": event["timestamp"],
            "source": source,
            "message": message,
        })
        del runtime_errors[:-100]

    if level in {"warning", "error"} or source in TERMINAL_LOG_SOURCES:
        log_method = terminal_logger.error if level == "error" else terminal_logger.info
        log_method("[%s] %s", source, message)


def log_error(message: str, source: str = "System"):
    log_event("error", source, message)


def write_prompt_log(kind: str, prompt: str, metadata: Optional[dict] = None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{kind}.json"
    path = PROMPT_LOGS_DIR / filename
    payload = {
        "timestamp": datetime.now().isoformat(),
        "kind": kind,
        "prompt": prompt,
        "metadata": metadata or {},
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def truncate_for_log(value, limit: int = 1200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def extract_openrouter_text_content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("text"), str):
                text_parts.append(item["text"])
                continue
            if item.get("type") == "text" and isinstance(item.get("content"), str):
                text_parts.append(item["content"])
        return "\n".join(part for part in text_parts if part)
    return ""


def format_replicate_error(data: dict) -> str:
    error_text = (data.get("error") or "").strip()
    if error_text:
        return f"Replicate prediction failed: {error_text}"

    status = data.get("status") or "unknown"
    prediction_id = data.get("id") or "unknown"
    model = data.get("model") or "unknown"
    version = data.get("version") or "unknown"
    logs = (data.get("logs") or "").strip()
    metrics = data.get("metrics") or {}
    total_time = metrics.get("total_time")
    output = data.get("output")

    reason = "Unknown failure"
    if logs:
        log_lines = [line.strip() for line in logs.splitlines() if line.strip()]
        if log_lines:
            reason = log_lines[-1]
            if reason.lower().endswith("readtimeout") or "readtimeout" in reason.lower():
                reason = "Upstream image generation timed out"
    elif output is None:
        reason = "No output returned"

    lines = [
        "Replicate prediction failed",
        f"Reason: {reason}",
        f"Status: {status}",
        f"Prediction ID: {prediction_id}",
        f"Model: {model}",
    ]

    if version and version != "hidden":
        lines.append(f"Version: {version}")
    if total_time is not None:
        lines.append(f"Duration: {total_time:.1f}s")
    if logs:
        lines.append("Logs:")
        lines.extend(f"  {line}" for line in log_lines[-4:])

    web_url = (data.get("urls") or {}).get("web")
    if web_url:
        lines.append(f"Replicate URL: {web_url}")

    return "\n".join(lines)


def format_replicate_http_error(exc: httpx.HTTPStatusError) -> str:
    status_code = exc.response.status_code
    try:
        data = exc.response.json()
    except ValueError:
        data = None

    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str) and detail.strip():
            return f"Replicate request failed ({status_code}): {detail.strip()}"
        if detail is not None:
            return f"Replicate request failed ({status_code}): {json.dumps(detail, ensure_ascii=True)}"
        error = data.get("error")
        if isinstance(error, str) and error.strip():
            return f"Replicate request failed ({status_code}): {error.strip()}"
        return f"Replicate request failed ({status_code}): {json.dumps(data, ensure_ascii=True)}"

    body_text = exc.response.text.strip()
    if body_text:
        return f"Replicate request failed ({status_code}): {body_text}"
    return f"Replicate request failed ({status_code})"


def get_default_pipeline_id() -> str:
    return ensure_config()["default_pipeline_id"]


def get_debug_mode() -> bool:
    return bool(ensure_config().get("debug_mode", False))


def get_skip_image_generation() -> bool:
    return bool(ensure_config().get("skip_image_generation", False))


def get_watcher_enabled() -> bool:
    return bool(ensure_config().get("watcher_enabled", True))


def get_watched_folder_setting() -> str:
    return str(ensure_config().get("watched_folder") or "watch/")


def resolve_watched_folder_path(folder_setting: Optional[str] = None) -> Path:
    raw_value = str(folder_setting or get_watched_folder_setting()).strip() or "watch/"
    if raw_value in {"/watch", "watch", "watch/"}:
        path = DEFAULT_WATCH_DIR
    else:
        candidate = Path(raw_value).expanduser()
        path = candidate if candidate.is_absolute() else (Path(__file__).parent / candidate).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_watch_dir() -> Path:
    return resolve_watched_folder_path()


async def choose_folder_via_dialog(initial_path: Optional[Path] = None) -> Optional[str]:
    if sys.platform != "darwin":
        raise HTTPException(501, "Folder chooser is only supported on macOS")

    script_lines = []
    if initial_path:
        escaped_initial_path = str(initial_path).replace("\\", "\\\\").replace('"', '\\"')
        script_lines.extend([
            f'set defaultFolder to POSIX file "{escaped_initial_path}"',
            'set chosenFolder to choose folder with prompt "Choose watched folder" default location defaultFolder',
        ])
    else:
        script_lines.append('set chosenFolder to choose folder with prompt "Choose watched folder"')
    script_lines.append("POSIX path of chosenFolder")

    args = ["osascript"]
    for line in script_lines:
        args.extend(["-e", line])

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    stdout_text = (stdout or b"").decode("utf-8", errors="replace").strip()
    stderr_text = (stderr or b"").decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        lower_error = stderr_text.lower()
        if "user canceled" in lower_error or "user cancelled" in lower_error:
            return None
        raise HTTPException(500, stderr_text or "Folder chooser failed")

    return stdout_text or None


def get_text_model() -> str:
    return str(ensure_config().get("text_model", "anthropic/claude-opus-4.6"))


def get_variety_compression_prompt() -> str:
    return str(ensure_config()["variety_compression_prompt"])


def get_text_model_option() -> dict:
    option = TEXT_MODELS.get(get_text_model())
    if not option:
        return TEXT_MODELS["anthropic/claude-opus-4.6"]
    return option


def get_image_model_option(option_id: str) -> dict:
    option = IMAGE_MODELS.get(option_id)
    if not option:
        raise HTTPException(400, "Invalid image model")
    return option


def get_default_image_model() -> str:
    return str(ensure_config().get("image_model", "replicate:google/nano-banana-pro"))


def get_default_aspect_ratio() -> str:
    image_model = get_default_image_model()
    allowed_aspect_ratios = get_allowed_aspect_ratios(image_model)
    aspect_ratio = str(ensure_config().get("aspect_ratio", "3:4"))
    if aspect_ratio not in allowed_aspect_ratios:
        return "3:4" if "3:4" in allowed_aspect_ratios else sorted(allowed_aspect_ratios)[0]
    return aspect_ratio


def get_default_run_count() -> int:
    try:
        run_count = int(ensure_config().get("run_count", 1))
    except Exception:
        run_count = 1
    return max(1, min(20, run_count))


def get_allowed_aspect_ratios(image_model: str) -> set[str]:
    return MODEL_ASPECT_RATIOS.get(image_model, ASPECT_RATIOS)


def get_encourage_variety_within_batches() -> bool:
    return bool(ensure_config().get("encourage_variety_within_batches", False))


def get_encourage_variety_across_session() -> bool:
    return bool(ensure_config().get("encourage_variety_across_session", False))


def get_layout_settings() -> dict:
    return dict(ensure_config().get("layout", {}))


def get_http_access_logging() -> bool:
    return bool(ensure_config().get("http_access_logging", False))


def get_printer_name() -> str:
    return str(ensure_config().get("printer_name") or "")


def get_send_to_printer() -> bool:
    return bool(ensure_config().get("send_to_printer", False))


def get_print_orientation() -> str:
    return str(ensure_config().get("print_orientation") or "portrait")


def get_print_fit_mode() -> str:
    return str(ensure_config().get("print_fit_mode") or "default")


def list_available_printers() -> list[str]:
    try:
        result = subprocess.run(
            ["lpstat", "-a"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    except Exception as exc:
        log_error(f"Could not list printers: {exc}", "System")
        return []

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if stderr:
            log_error(f"Printer discovery failed: {stderr}", "System")
        return []

    printers: list[str] = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        printer_name = line.split()[0]
        if printer_name and printer_name not in printers:
            printers.append(printer_name)
    return printers


def job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def normalize_job(job: dict) -> dict:
    normalized = dict(job)
    normalized.setdefault("extracted_concepts", "")
    normalized.setdefault("intermediate_prompt", "")
    normalized.setdefault("batch_variety_text", "")
    normalized.setdefault("session_variety_text", "")
    normalized.setdefault("variety_guidance_text", "")
    normalized.setdefault("meaningful_difference_text", "")
    normalized.setdefault("resolved_interpretation_prompt", "")
    normalized.setdefault("resolved_image_prompt", "")
    normalized.setdefault("output_filename", None)
    normalized.setdefault("output_filenames", [])
    normalized.setdefault("print_status", None)
    normalized.setdefault("printed_at", None)
    normalized.setdefault("print_error", None)
    normalized.setdefault("error", None)
    normalized.setdefault("message", "")
    normalized.setdefault("generation_started_at", None)
    normalized.setdefault("generation_estimate_seconds", None)
    normalized.setdefault("generation_last_duration_seconds", None)
    return normalized


def save_job(job: dict):
    job = normalize_job(job)
    path = job_path(job["id"])
    with open(path, "w") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)


def load_job(job_id: str) -> dict:
    path = job_path(job_id)
    if not path.exists():
        raise HTTPException(404, f"Job not found: {job_id}")

    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HTTPException(500, f"Job file is invalid: {job_id}")
    return normalize_job(data)


def list_jobs(limit: Optional[int] = None) -> list[dict]:
    jobs = []
    for path in JOBS_DIR.glob("*.json"):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                jobs.append(normalize_job(data))
        except Exception as exc:
            log_error(f"Could not read job file {path.name}: {exc}", "Jobs")

    jobs.sort(key=lambda job: job.get("created_at") or "", reverse=True)
    if isinstance(limit, int) and limit > 0:
        return jobs[:limit]
    return jobs


def update_job(job_id: str, **updates) -> dict:
    job = load_job(job_id)
    job.update(updates)
    save_job(job)
    return job


def create_job(
    *,
    trigger: str,
    source_images: list[str],
    pipeline: dict,
    text_model: str,
    image_model: str,
    printer_name: str,
    send_to_printer: bool,
    print_orientation: str,
    print_fit_mode: str,
    aspect_ratio: str,
    run_count: int,
    encourage_variety_within_batches: bool,
    encourage_variety_across_session: bool,
    skip_image_generation: bool,
) -> dict:
    created_at = datetime.now().isoformat()
    job = {
        "id": uuid4().hex,
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "status": "queued",
        "trigger": trigger,
        "source_images": list(source_images),
        "pipeline_id": pipeline["id"],
        "pipeline_name": pipeline["name"],
        "interpretation_prompt": pipeline["interpretation"],
        "image_generation_prompt": pipeline["image"],
        "settings_snapshot": {
            "text_model": text_model,
            "image_model": image_model,
            "printer_name": printer_name,
            "send_to_printer": send_to_printer,
            "print_orientation": print_orientation,
            "print_fit_mode": print_fit_mode,
            "aspect_ratio": aspect_ratio,
            "run_count": run_count,
            "encourage_variety_within_batches": encourage_variety_within_batches,
            "encourage_variety_across_session": encourage_variety_across_session,
            "skip_image_generation": skip_image_generation,
        },
        "extracted_concepts": "",
        "intermediate_prompt": "",
        "batch_variety_text": "",
        "session_variety_text": "",
        "variety_guidance_text": "",
        "meaningful_difference_text": "",
        "resolved_interpretation_prompt": "",
        "resolved_image_prompt": "",
        "output_filename": None,
        "output_filenames": [],
        "print_status": None,
        "printed_at": None,
        "print_error": None,
        "generation_started_at": None,
        "generation_estimate_seconds": None,
        "generation_last_duration_seconds": None,
        "error": None,
        "message": "Queued",
    }
    save_job(job)
    return job


def list_pipeline_summaries() -> list[dict]:
    pipelines = []
    for pipeline_id in list_viable_pipeline_ids():
        pipeline = load_pipeline(pipeline_id)
        pipelines.append({
            "id": pipeline["id"],
            "name": pipeline["name"],
            "path": pipeline["path"],
        })
    return pipelines


def load_pipeline(pipeline_id: str) -> dict:
    path = resolve_pipeline_path(pipeline_id)
    return parse_pipeline_markdown(path.read_text(), path.stem)


def save_pipeline(pipeline_id: str, name: str, interpretation: str, image: str) -> dict:
    if not interpretation.strip() or not image.strip():
        raise HTTPException(400, "Both prompts are required")

    path = pipeline_path(pipeline_id)
    pipeline_id = path.stem
    content = render_pipeline_markdown(name or pipeline_id.replace("-", " ").title(), interpretation, image)
    path.write_text(content)
    return load_pipeline(pipeline_id)


def create_pipeline(name: str) -> dict:
    clean_name = (name or "").strip()
    if not clean_name:
        raise HTTPException(400, "Pipeline name is required")

    pipeline_id = slugify(clean_name)
    path = pipeline_path(pipeline_id)
    if path.exists():
        raise HTTPException(400, f"Pipeline already exists: {pipeline_id}")

    path.write_text(build_pipeline_boilerplate(clean_name))
    return load_pipeline(pipeline_id)


# --- App state ---

ensure_default_pipeline()
ensure_config()
current_pipeline_id = get_default_pipeline_id()
current_pipeline = load_pipeline(current_pipeline_id)
pipeline_task: Optional[asyncio.Task] = None
job_queue: Optional[asyncio.Queue] = None
watcher_task: Optional[asyncio.Task] = None
queue_worker_task: Optional[asyncio.Task] = None
queue_worker_current_item: Optional[dict] = None
known_watch_signatures: dict[str, tuple[int, int]] = {}
pending_watch_candidates: dict[str, dict] = {}
queued_watch_files: set[str] = set()
image_generation_duration_seconds_history: list[float] = []

WATCH_POLL_INTERVAL_SECONDS = 2.0
WATCH_STABLE_POLLS = 2
DEFAULT_IMAGE_GENERATION_ESTIMATE_SECONDS = 30.0


def get_image_generation_estimate_seconds() -> float:
    if not image_generation_duration_seconds_history:
        return DEFAULT_IMAGE_GENERATION_ESTIMATE_SECONDS
    return sum(image_generation_duration_seconds_history) / len(image_generation_duration_seconds_history)


def log_queue_length_change(context: str):
    if job_queue is None:
        return
    log_event("info", "System", f"Queue length changed to {job_queue.qsize()} ({context})")


def snapshot_job_queue_items() -> list[dict]:
    if job_queue is None:
        return []
    raw_items = list(getattr(job_queue, "_queue", []))
    items: list[dict] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        job_id = str(raw.get("job_id") or "").strip()
        filename = str(raw.get("filename") or "").strip()
        summary = {
            "job_id": job_id,
            "filename": filename,
        }
        if job_id:
            try:
                job = load_job(job_id)
                summary.update({
                    "created_at": job.get("created_at"),
                    "pipeline_id": job.get("pipeline_id"),
                    "pipeline_name": job.get("pipeline_name"),
                    "source_images": job.get("source_images") or [],
                    "trigger": job.get("trigger"),
                    "status": job.get("status"),
                })
            except HTTPException:
                pass
        items.append(summary)
    return items


def get_queue_status_payload() -> dict:
    current_item = dict(queue_worker_current_item) if isinstance(queue_worker_current_item, dict) else None
    if current_item:
        job_id = str(current_item.get("job_id") or "").strip()
        if job_id:
            try:
                job = load_job(job_id)
                current_item.update({
                    "created_at": job.get("created_at"),
                    "pipeline_id": job.get("pipeline_id"),
                    "pipeline_name": job.get("pipeline_name"),
                    "source_images": job.get("source_images") or [],
                    "trigger": job.get("trigger"),
                    "status": job.get("status"),
                })
            except HTTPException:
                pass
    return {
        "worker_running": queue_worker_task is not None and not queue_worker_task.done(),
        "queued_count": job_queue.qsize() if job_queue is not None else 0,
        "queued_items": snapshot_job_queue_items(),
        "current_item": current_item,
    }

pipeline_state = {
    "job_id": None,
    "status": "idle",  # idle | interpreting | generating | downloading | printing | cancelling | complete | cancelled | error
    "message": "",
    "description": None,
    "poster_filename": None,
    "poster_filenames": [],
    "error": None,
    "started_at": None,
    "source_images": [],
    "pipeline_id": current_pipeline_id,
    "image_model": get_default_image_model(),
    "aspect_ratio": get_default_aspect_ratio(),
    "send_to_printer": get_send_to_printer(),
    "run_count": get_default_run_count(),
    "completed_runs": 0,
    "current_run": 0,
    "rerun_interpretation": False,
    "encourage_variety_within_batches": get_encourage_variety_within_batches(),
    "encourage_variety_across_session": get_encourage_variety_across_session(),
    "job_interpretation_history": [],
    "job_variety_text": "",
    "session_interpretation_history": [],
    "session_variety_text": "",
    "variety_guidance_text": "",
    "meaningful_difference_text": "",
    "extracted_concepts": "",
    "generation_started_at": None,
    "generation_estimate_seconds": None,
    "generation_last_duration_seconds": None,
    "cancel_requested": False,
}


def clear_session_variety_state() -> None:
    pipeline_state["session_interpretation_history"] = []
    pipeline_state["session_variety_text"] = ""
    pipeline_state["variety_guidance_text"] = pipeline_state.get("job_variety_text") or ""
    pipeline_state["meaningful_difference_text"] = pipeline_state["variety_guidance_text"]


# --- FastAPI app ---

app = FastAPI(title="Dementia Design Poster Generator")


@app.on_event("startup")
async def startup_event():
    global job_queue, watcher_task, queue_worker_task, known_watch_signatures, pending_watch_candidates, queued_watch_files
    job_queue = asyncio.Queue()
    pending_watch_candidates = {}
    queued_watch_files = set()
    await start_queue_worker()
    await sync_watcher_state("startup")


@app.on_event("shutdown")
async def shutdown_event():
    global watcher_task, queue_worker_task, job_queue
    for task in (watcher_task, queue_worker_task):
        if task is not None:
            task.cancel()
    for task in (watcher_task, queue_worker_task):
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
    watcher_task = None
    queue_worker_task = None
    job_queue = None


# --- Helper functions ---

def get_image_files() -> list[Path]:
    """Return all image files in the watch directory, newest first."""
    files = []
    watch_dir = get_watch_dir()
    for f in watch_dir.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(f)
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def resolve_selected_images(filenames: list[str]) -> list[Path]:
    """Resolve a list of selected filenames to safe paths inside the watch directory."""
    available = {path.name: path for path in get_image_files()}
    selected_paths = []

    for filename in filenames:
        if filename not in available:
            raise HTTPException(400, f"Image not found in watch folder: {filename}")
        selected_paths.append(available[filename])

    return selected_paths


def get_watch_signatures() -> dict[str, tuple[int, int]]:
    signatures = {}
    for path in get_image_files():
        stat = path.stat()
        signatures[path.name] = (stat.st_size, stat.st_mtime_ns)
    return signatures


def get_current_operational_settings() -> dict:
    pipeline_id = pipeline_state.get("pipeline_id") or current_pipeline_id or get_default_pipeline_id()
    pipeline = load_pipeline(pipeline_id)
    image_model = pipeline_state.get("image_model") or get_default_image_model()
    aspect_ratio = str(pipeline_state.get("aspect_ratio") or get_default_aspect_ratio())
    allowed_aspect_ratios = get_allowed_aspect_ratios(image_model)
    if aspect_ratio not in allowed_aspect_ratios:
        aspect_ratio = "3:4" if "3:4" in allowed_aspect_ratios else sorted(allowed_aspect_ratios)[0]
    run_count = int(pipeline_state.get("run_count") or get_default_run_count())
    run_count = max(1, min(20, run_count))
    encourage_variety_within_batches = bool(pipeline_state.get("encourage_variety_within_batches", False))
    encourage_variety_across_session = bool(pipeline_state.get("encourage_variety_across_session", False))
    return {
        "pipeline": pipeline,
        "text_model": get_text_model(),
        "image_model": image_model,
        "printer_name": get_printer_name(),
        "send_to_printer": get_send_to_printer(),
        "print_orientation": get_print_orientation(),
        "print_fit_mode": get_print_fit_mode(),
        "aspect_ratio": aspect_ratio,
        "run_count": run_count,
        "encourage_variety_within_batches": encourage_variety_within_batches,
        "encourage_variety_across_session": encourage_variety_across_session,
        "skip_image_generation": get_skip_image_generation(),
    }


def get_current_run_config() -> dict:
    pipeline_id = pipeline_state.get("pipeline_id") or current_pipeline_id or get_default_pipeline_id()
    image_model = pipeline_state.get("image_model") or get_default_image_model()
    allowed_aspect_ratios = get_allowed_aspect_ratios(image_model)
    aspect_ratio = str(pipeline_state.get("aspect_ratio") or get_default_aspect_ratio())
    if aspect_ratio not in allowed_aspect_ratios:
        aspect_ratio = "3:4" if "3:4" in allowed_aspect_ratios else sorted(allowed_aspect_ratios)[0]
    run_count = max(1, min(20, int(pipeline_state.get("run_count") or get_default_run_count())))
    encourage_variety_within_batches = bool(pipeline_state.get("encourage_variety_within_batches", False))
    encourage_variety_across_session = bool(pipeline_state.get("encourage_variety_across_session", False))
    return {
        "pipeline_id": pipeline_id,
        "image_model": image_model,
        "aspect_ratio": aspect_ratio,
        "run_count": run_count,
        "encourage_variety_within_batches": encourage_variety_within_batches,
        "encourage_variety_across_session": encourage_variety_across_session,
        "send_to_printer": get_send_to_printer(),
    }


async def stop_watcher(reason: Optional[str] = None):
    global watcher_task, known_watch_signatures, pending_watch_candidates, queued_watch_files
    task = watcher_task
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    watcher_task = None
    known_watch_signatures = {}
    pending_watch_candidates = {}
    queued_watch_files = set()
    if reason:
        log_event("info", "System", reason)


async def start_watcher(reason: Optional[str] = None):
    global watcher_task, known_watch_signatures, pending_watch_candidates, queued_watch_files
    if watcher_task is not None and not watcher_task.done():
        return
    known_watch_signatures = get_watch_signatures()
    pending_watch_candidates = {}
    queued_watch_files = set()
    watcher_task = asyncio.create_task(watch_folder_loop())
    if reason:
        log_event("info", "System", reason)


async def sync_watcher_state(reason: Optional[str] = None, force_restart: bool = False):
    if get_watcher_enabled():
        if force_restart and watcher_task is not None and not watcher_task.done():
            await stop_watcher()
        await start_watcher(reason)
    else:
        await stop_watcher(reason)


async def stop_queue_worker(reason: Optional[str] = None, reset_queue: bool = False):
    global queue_worker_task, queue_worker_current_item, job_queue
    task = queue_worker_task
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    queue_worker_task = None
    queue_worker_current_item = None
    if reset_queue or job_queue is None:
        job_queue = asyncio.Queue()
    if reason:
        log_event("info", "System", reason)


async def start_queue_worker(reason: Optional[str] = None):
    global queue_worker_task, job_queue
    if job_queue is None:
        job_queue = asyncio.Queue()
    if queue_worker_task is not None and not queue_worker_task.done():
        return
    queue_worker_task = asyncio.create_task(process_job_queue())
    if reason:
        log_event("info", "System", reason)


def launch_pipeline_job(
    job: dict,
    images: list[Path],
    pipeline: dict,
    image_model_option: dict,
):
    global pipeline_task

    settings_snapshot = job.get("settings_snapshot") or {}
    aspect_ratio = str(settings_snapshot.get("aspect_ratio") or "3:4")
    run_count = int(settings_snapshot.get("run_count") or 1)
    effective_rerun_interpretation = run_count > 1
    effective_encourage_variety_within_batches = bool(settings_snapshot.get("encourage_variety_within_batches", False))
    effective_encourage_variety_across_session = bool(settings_snapshot.get("encourage_variety_across_session", False))
    existing_session_interpretation_history = (
        list(pipeline_state.get("session_interpretation_history") or [])
        if effective_encourage_variety_across_session
        else []
    )
    existing_session_variety_text = (
        pipeline_state.get("session_variety_text") or ""
        if effective_encourage_variety_across_session
        else ""
    )

    pipeline_state.update({
        "job_id": job["id"],
        "status": "interpreting",
        "message": f"Sending {len(images)} image(s) to Claude for interpretation...",
        "description": None,
        "poster_filename": None,
        "poster_filenames": [],
        "error": None,
        "started_at": datetime.now().isoformat(),
        "source_images": list(job.get("source_images") or []),
        "pipeline_id": pipeline["id"],
        "image_model": settings_snapshot.get("image_model", get_default_image_model()),
        "aspect_ratio": aspect_ratio,
        "send_to_printer": bool(settings_snapshot.get("send_to_printer", get_send_to_printer())),
        "run_count": run_count,
        "completed_runs": 0,
        "current_run": 0,
        "rerun_interpretation": effective_rerun_interpretation,
        "encourage_variety_within_batches": effective_encourage_variety_within_batches,
        "encourage_variety_across_session": effective_encourage_variety_across_session,
        "job_interpretation_history": [],
        "job_variety_text": "",
        "session_interpretation_history": existing_session_interpretation_history,
        "session_variety_text": existing_session_variety_text,
        "variety_guidance_text": "",
        "meaningful_difference_text": existing_session_variety_text,
        "extracted_concepts": "",
        "cancel_requested": False,
    })

    pipeline_task = asyncio.create_task(
        _run_pipeline(
            job["id"],
            images,
            pipeline,
            image_model_option,
            aspect_ratio,
            run_count,
            effective_rerun_interpretation,
            effective_encourage_variety_within_batches,
            effective_encourage_variety_across_session,
        )
    )


async def enqueue_watch_job(filename: str) -> dict:
    if job_queue is None:
        raise RuntimeError("Job queue is not initialized")

    settings = get_current_operational_settings()
    pipeline = settings["pipeline"]
    job = create_job(
        trigger="watch",
        source_images=[filename],
        pipeline=pipeline,
        text_model=settings["text_model"],
        image_model=settings["image_model"],
        printer_name=settings["printer_name"],
        send_to_printer=settings["send_to_printer"],
        print_orientation=settings["print_orientation"],
        print_fit_mode=settings["print_fit_mode"],
        aspect_ratio=settings["aspect_ratio"],
        run_count=settings["run_count"],
        encourage_variety_within_batches=settings["encourage_variety_within_batches"],
        encourage_variety_across_session=settings["encourage_variety_across_session"],
        skip_image_generation=settings["skip_image_generation"],
    )
    queued_watch_files.add(filename)
    log_event(
        "info",
        "Watch Folder",
        "\n".join([
            "Job created from new file",
            f"Filename: {filename}",
            f"Job ID: {job['id']}",
            f"Pipeline: {pipeline['name']}",
            f"Image model: {settings['image_model']}",
            f"Aspect ratio: {settings['aspect_ratio']}",
            f"Run count: {settings['run_count']}",
        ]),
        job_id=job["id"],
        filename=filename,
        pipeline_id=pipeline["id"],
    )
    await job_queue.put({
        "job_id": job["id"],
        "filename": filename,
    })
    log_queue_length_change("job created")
    return job


async def watch_folder_loop():
    global known_watch_signatures, pending_watch_candidates
    watch_dir = get_watch_dir()
    log_event(
        "info",
        "Watch Folder",
        "\n".join([
            "Watch folder ready",
            f"Folder: {watch_dir}",
            f"Baseline file count: {len(known_watch_signatures)}",
        ]),
    )
    try:
        while True:
            current_signatures = get_watch_signatures()

            removed_filenames = set(known_watch_signatures) - set(current_signatures)
            for filename in removed_filenames:
                log_event("info", "Watch Folder", f"Source file removed or consumed: {filename}", filename=filename)
                known_watch_signatures.pop(filename, None)
                pending_watch_candidates.pop(filename, None)
                queued_watch_files.discard(filename)

            for filename, signature in current_signatures.items():
                if known_watch_signatures.get(filename) == signature:
                    continue
                if filename in queued_watch_files:
                    continue

                candidate = pending_watch_candidates.get(filename)
                if candidate and candidate.get("signature") == signature:
                    candidate["stable_polls"] = int(candidate.get("stable_polls", 0)) + 1
                else:
                    pending_watch_candidates[filename] = {
                        "signature": signature,
                        "stable_polls": 1,
                    }
                    log_event(
                        "info",
                        "Watch Folder",
                        "\n".join([
                            "New file detected",
                            f"Filename: {filename}",
                            f"Size: {signature[0]}",
                        ]),
                        filename=filename,
                    )
                    continue

                if pending_watch_candidates[filename]["stable_polls"] >= WATCH_STABLE_POLLS:
                    log_event(
                        "info",
                        "Watch Folder",
                        f"File stable: {filename}",
                        filename=filename,
                    )
                    await enqueue_watch_job(filename)
                    known_watch_signatures[filename] = signature
                    pending_watch_candidates.pop(filename, None)

            await asyncio.sleep(WATCH_POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log_error(f"Watch folder stopped unexpectedly: {exc}", "System")
        raise


async def process_job_queue():
    global job_queue, queue_worker_current_item
    log_event("info", "Jobs", "Job worker ready")
    try:
        while True:
            if job_queue is None:
                await asyncio.sleep(1)
                continue

            item = await job_queue.get()
            queue_worker_current_item = dict(item) if isinstance(item, dict) else None
            log_queue_length_change("job started")
            job_id = item.get("job_id")
            filename = item.get("filename")
            try:
                while pipeline_task is not None or pipeline_state["status"] not in ("idle", "complete", "cancelled", "error"):
                    await asyncio.sleep(1)

                job = load_job(job_id)
                settings_snapshot = job.get("settings_snapshot") or {}
                image_model = str(settings_snapshot.get("image_model") or get_default_image_model())
                image_model_option = get_image_model_option(image_model)
                images = resolve_selected_images(list(job.get("source_images") or []))
                pipeline = {
                    "id": job["pipeline_id"],
                    "name": job.get("pipeline_name") or job["pipeline_id"],
                    "interpretation": job.get("interpretation_prompt") or load_pipeline(job["pipeline_id"])["interpretation"],
                    "image": job.get("image_generation_prompt") or load_pipeline(job["pipeline_id"])["image"],
                    "path": str(resolve_pipeline_path(job["pipeline_id"])),
                }
                log_event(
                    "info",
                    "Jobs",
                    "\n".join([
                        "Job started",
                        f"Filename: {filename or '(unknown)'}",
                        f"Job ID: {job_id}",
                        f"Pipeline: {pipeline['name']}",
                        f"Image model: {image_model}",
                    ]),
                    job_id=job_id,
                    filename=filename,
                    pipeline_id=pipeline["id"],
                )
                launch_pipeline_job(job, images, pipeline, image_model_option)
                if pipeline_task is not None:
                    await pipeline_task
            except HTTPException as exc:
                if exc.status_code == 404:
                    log_event(
                        "warning",
                        "System",
                        f"Dropped stale queued job {job_id} because its job file was not found",
                        job_id=job_id,
                        filename=filename,
                    )
                    continue
                raise
            except asyncio.CancelledError:
                if pipeline_state.get("status") == "cancelled":
                    log_event(
                        "info",
                        "Jobs",
                        f"Cancelled job {job_id} was released by the worker",
                        job_id=job_id,
                        filename=filename,
                        pipeline_id=job.get("pipeline_id") if 'job' in locals() and isinstance(job, dict) else None,
                    )
                    continue
                raise
            except Exception as exc:
                log_error(f"Job {job_id} failed before processing started: {exc}", "Jobs")
                update_job(
                    job_id,
                    status="error",
                    completed_at=datetime.now().isoformat(),
                    error=str(exc),
                    message=f"Error: {exc}",
                )
            finally:
                if filename:
                    queued_watch_files.discard(filename)
                queue_worker_current_item = None
                if job_queue is not None:
                    job_queue.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log_error(f"Job worker stopped unexpectedly: {exc}", "System")
        raise


def resolve_watch_image(filename: str) -> Path:
    """Resolve a single safe watch-folder image path."""
    if not filename:
        raise HTTPException(400, "No filename provided")

    for path in get_image_files():
        if path.name == filename:
            return path

    raise HTTPException(404, f"Image not found in watch folder: {filename}")


def resolve_output_image(filename: str) -> Path:
    """Resolve a single safe output-folder image path."""
    if not filename:
        raise HTTPException(400, "No filename provided")

    path = OUTPUT_DIR / Path(filename).name
    if not path.exists() or not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise HTTPException(404, f"Output image not found: {filename}")
    return path


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def save_base64_image(data_url: str, filename_prefix: str = "webcam") -> str:
    """Decode a data URL image and save it into the watch directory."""
    if not data_url.startswith("data:image/"):
        raise HTTPException(400, "Invalid image payload")

    try:
        header, encoded = data_url.split(",", 1)
    except ValueError as exc:
        raise HTTPException(400, "Malformed image payload") from exc

    mime_type = header.split(";")[0].removeprefix("data:")
    extension = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }.get(mime_type)

    if not extension:
        raise HTTPException(400, f"Unsupported image type: {mime_type}")

    try:
        image_bytes = base64.b64decode(encoded)
    except Exception as exc:
        raise HTTPException(400, "Could not decode image payload") from exc

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{filename_prefix}_{timestamp}{extension}"
    output_path = get_watch_dir() / filename

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    return filename


async def save_uploaded_image(file: UploadFile) -> str:
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        raise HTTPException(400, "Unsupported image type")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Uploaded file is empty")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"upload_{timestamp}{extension}"
    output_path = get_watch_dir() / filename
    with open(output_path, "wb") as f:
        f.write(contents)
    return filename


def requeue_watch_images(source_filenames: list[str]) -> list[str]:
    copied_filenames: list[str] = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    for index, source_filename in enumerate(source_filenames, start=1):
        source_path = resolve_watch_image(source_filename)
        extension = source_path.suffix.lower()
        copied_filename = f"requeue_{timestamp}_{index}{extension}"
        output_path = get_watch_dir() / copied_filename
        shutil.copy2(source_path, output_path)
        copied_filenames.append(copied_filename)

    return copied_filenames


def copy_output_image_to_watch(output_filename: str, filename_prefix: str = "feedback") -> str:
    source_path = resolve_output_image(output_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    copied_filename = f"{filename_prefix}_{timestamp}{source_path.suffix.lower()}"
    output_path = get_watch_dir() / copied_filename
    shutil.copy2(source_path, output_path)
    return copied_filename


def build_png_job_metadata(job: dict) -> dict[str, str]:
    return {
        "job_json": json.dumps(job, ensure_ascii=False),
    }


def build_library_index() -> list[dict]:
    """Return poster-library entries derived directly from output files."""
    entries = []
    for path in sorted(OUTPUT_DIR.iterdir(), key=lambda file_path: file_path.stat().st_mtime, reverse=True):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        metadata = read_output_metadata(path)
        job = metadata.get("job") or {}
        settings_snapshot = job.get("settings_snapshot") or {}
        created_at = (
            job.get("completed_at")
            or job.get("created_at")
            or datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        )
        source_images = [str(item) for item in (job.get("source_images") or [])]

        entries.append({
            "poster_filename": path.name,
            "description": job.get("intermediate_prompt"),
            "extracted_concepts": job.get("extracted_concepts"),
            "created_at": created_at,
            "source_images": source_images,
            "pipeline_id": job.get("pipeline_id"),
            "pipeline_name": job.get("pipeline_name"),
            "interpretation_prompt": job.get("interpretation_prompt"),
            "image_generation_prompt": job.get("image_generation_prompt"),
            "resolved_image_generation_prompt": job.get("resolved_image_prompt"),
            "image_model": settings_snapshot.get("image_model"),
            "aspect_ratio": settings_snapshot.get("aspect_ratio"),
            "job_json": job,
        })

    return entries


def get_library_archive_directories() -> dict[str, Path]:
    return {
        "jobs": JOBS_DIR,
        "watch": get_watch_dir(),
        "output": OUTPUT_DIR,
    }


def iter_library_archive_files() -> list[tuple[Path, str]]:
    archive_files: list[tuple[Path, str]] = []
    for archive_folder, base_dir in get_library_archive_directories().items():
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(base_dir).as_posix()
            archive_files.append((path, f"{archive_folder}/{relative_path}"))
    return archive_files


def clear_directory_contents(directory: Path) -> None:
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        return
    for child in directory.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def resolve_library_import_target(member_name: str) -> Optional[Path]:
    member_path = Path(member_name)
    parts = [part for part in member_path.parts if part not in ("", ".")]
    if not parts:
        return None
    if any(part == ".." for part in parts):
        raise HTTPException(400, "Invalid archive entry")

    archive_folder = parts[0]
    base_dir = get_library_archive_directories().get(archive_folder)
    if base_dir is None:
        return None

    relative_parts = parts[1:]
    if not relative_parts:
        return None

    target = (base_dir / Path(*relative_parts)).resolve()
    if target != base_dir.resolve() and base_dir.resolve() not in target.parents:
        raise HTTPException(400, "Invalid archive entry")

    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def parse_source_images(value: Optional[str]) -> list[str]:
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    return [str(item) for item in parsed]


def read_output_metadata(path: Path) -> dict:
    if path.suffix.lower() != ".png":
        return {}

    try:
        with Image.open(path) as image:
            info = getattr(image, "info", {}) or {}
    except Exception as exc:
        log_error(f"Could not read metadata from {path.name}: {exc}", "System")
        return {}

    metadata = {}
    job_json = info.get("job_json")
    if isinstance(job_json, str) and job_json.strip():
        try:
            parsed_job = json.loads(job_json)
            if isinstance(parsed_job, dict):
                metadata["job"] = normalize_job(parsed_job)
        except json.JSONDecodeError:
            log_error(f"Could not parse embedded job_json from {path.name}", "System")
    if "job" not in metadata:
        legacy = {}
        for key in (
            "pipeline_id",
            "pipeline_name",
            "interpretation_prompt",
            "description",
            "extracted_concepts",
            "image_generation_prompt",
            "resolved_image_generation_prompt",
            "image_model",
            "aspect_ratio",
            "source_images",
            "created_at",
        ):
            value = info.get(key)
            if isinstance(value, str) and value:
                legacy[key] = value
        if legacy:
            metadata["job"] = normalize_job({
                "id": "",
                "created_at": legacy.get("created_at"),
                "completed_at": legacy.get("created_at"),
                "status": "complete",
                "trigger": "",
                "source_images": parse_source_images(legacy.get("source_images")),
                "pipeline_id": legacy.get("pipeline_id"),
                "pipeline_name": legacy.get("pipeline_name"),
                "interpretation_prompt": legacy.get("interpretation_prompt"),
                "image_generation_prompt": legacy.get("image_generation_prompt"),
                "resolved_image_prompt": legacy.get("resolved_image_generation_prompt"),
                "intermediate_prompt": legacy.get("description"),
                "extracted_concepts": legacy.get("extracted_concepts"),
                "settings_snapshot": {
                    "image_model": legacy.get("image_model"),
                    "aspect_ratio": legacy.get("aspect_ratio"),
                },
                "output_filename": path.name,
                "output_filenames": [path.name],
            })
    return metadata
async def call_claude(
    images: list[Path],
    prompt: str,
    pipeline_name: str = "",
    run_number: Optional[int] = None,
    job_id: Optional[str] = None,
    encourage_variety: bool = False,
    previous_interpretations: Optional[list[str]] = None,
    meaningful_difference_text: str = "",
    prompt_kind: str = "interpretation",
) -> str:
    """Send images + prompt to Claude via OpenRouter and return the text response."""
    text_model_option = get_text_model_option()
    content = []
    for img_path in images:
        b64 = image_to_base64(img_path)
        media_type = get_media_type(img_path)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{b64}"
            },
        })
    prompt_text = prompt
    write_prompt_log(
        prompt_kind,
        prompt_text,
        metadata={
            "job_id": job_id,
            "pipeline_name": pipeline_name,
            "run_number": run_number,
            "model": text_model_option["model"],
            "image_count": len(images),
            "images": [path.name for path in images],
            "encourage_variety": encourage_variety,
            "previous_interpretation_count": len(previous_interpretations or []),
            "meaningful_difference_text_length": len(meaningful_difference_text.strip()),
        },
    )
    content.append({"type": "text", "text": prompt_text})

    payload = {
        "model": text_model_option["model"],
        "max_tokens": 16384,
        "messages": [
            {"role": "user", "content": content}
        ],
    }
    if text_model_option.get("reasoning"):
        payload["reasoning"] = text_model_option["reasoning"]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Dementia Poster Generator",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
        extracted_text = extract_openrouter_text_content(data)
        log_event(
            "info",
            "Processing",
            "\n".join([
                "Interpretation response received",
                f"Pipeline: {pipeline_name or '(unknown)'}",
                f"Run: {run_number if run_number is not None else '(unknown)'}",
                f"Model: {text_model_option['model']}",
                f"Image count: {len(images)}",
                f"Images: {', '.join(path.name for path in images) if images else '(none)'}",
                f"Prompt preview: {truncate_for_log(prompt_text, 400)}",
                f"Raw content type: {type(raw_content).__name__}",
                f"Extracted text length: {len(extracted_text.strip())}",
                f"Extracted text preview: {truncate_for_log(extracted_text.strip(), 500)}",
            ]),
        )
        if not extracted_text.strip():
            log_error(
                "\n".join([
                    "Interpretation returned blank content",
                    f"Pipeline: {pipeline_name or '(unknown)'}",
                    f"Run: {run_number if run_number is not None else '(unknown)'}",
                    f"Model: {text_model_option['model']}",
                    f"Image count: {len(images)}",
                    f"Images: {', '.join(path.name for path in images) if images else '(none)'}",
                    f"Prompt preview: {truncate_for_log(prompt_text, 500)}",
                    f"Response preview: {truncate_for_log(data, 1500)}",
                ]),
                "Processing",
            )
        return extracted_text


def require_description(description: Optional[str], pipeline_name: str, run_number: int) -> str:
    normalized = (description or "").strip()
    if normalized:
        return normalized
    raise Exception(
        f"Intermediate prompt was blank for run {run_number} using {pipeline_name}. "
        "Stopping before image generation."
    )


def require_extracted_concepts(concepts: Optional[str]) -> str:
    normalized = (concepts or "").strip()
    if normalized:
        return normalized
    raise Exception("Extracted concepts were blank. Stopping before interpretation.")


async def compress_meaningful_difference(
    previous_interpretations: list[str],
    pipeline_name: str,
    run_number: int,
    job_id: Optional[str] = None,
) -> str:
    raw_history = "\n\n".join(
        f"{idx + 1}. {item.strip()}"
        for idx, item in enumerate(previous_interpretations)
        if isinstance(item, str) and item.strip()
    ).strip()
    if not raw_history:
        return ""

    compressed = await call_claude(
        [],
        get_variety_compression_prompt().format(previous_interpretations=raw_history),
        pipeline_name=f"{pipeline_name} Meaningful Difference Compression",
        run_number=run_number,
        job_id=job_id,
        prompt_kind="meaningfuldifference-compression",
    )
    normalized = (compressed or "").strip()
    if normalized:
        return normalized

    log_error(
        f"Meaningful-difference compression was blank for run {run_number} using {pipeline_name}. Falling back to raw history.",
        "Processing",
    )
    return raw_history


def build_variety_guidance_prompt(
    base_prompt: str,
    *,
    extracted_concepts: str,
    batch_variety_text: str = "",
    session_variety_text: str = "",
) -> str:
    prompt = base_prompt.replace(EXTRACTED_CONCEPTS_TOKEN, extracted_concepts)
    prompt = prompt.replace(MEANINGFUL_DIFFERENCE_TOKEN, "").strip()

    sections: list[str] = []
    if batch_variety_text.strip():
        sections.append("\n".join([
            "### Variety Guidance",
            "Avoid these concepts:",
            batch_variety_text.strip(),
        ]))
    if session_variety_text.strip():
        sections.append("\n".join([
            "### Variety Guidance",
            "Avoid these concepts:",
            session_variety_text.strip(),
        ]))
    if not sections:
        return prompt
    return f"{prompt}\n\n" + "\n\n".join(sections)


async def call_replicate(
    prompt: str,
    model: str,
    aspect_ratio: str,
    prompt_metadata: Optional[dict] = None,
) -> str:
    """Send prompt to Replicate and return the output image URL."""
    write_prompt_log(
        "image-generation",
        prompt,
        metadata={
            "provider": "replicate",
            "model": model,
            "aspect_ratio": aspect_ratio,
            **(prompt_metadata or {}),
        },
    )
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
        }
    }

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        # Try sync mode first (waits up to 60s)
        try:
            resp = await client.post(
                f"https://api.replicate.com/v1/models/{model}/predictions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise Exception(format_replicate_http_error(exc)) from exc
        data = resp.json()

        # If not yet succeeded, poll
        if data.get("status") not in ("succeeded",):
            get_url = data.get("urls", {}).get("get")
            if not get_url:
                raise Exception(format_replicate_error(data))

            poll_headers = {
                "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            }
            for _ in range(60):  # poll for up to 5 minutes
                await asyncio.sleep(5)
                poll_resp = await client.get(get_url, headers=poll_headers)
                poll_resp.raise_for_status()
                data = poll_resp.json()
                if data["status"] == "succeeded":
                    break
                elif data["status"] == "failed":
                    raise Exception(format_replicate_error(data))
            else:
                raise Exception("Replicate prediction timed out after 5 minutes")

        # Extract output — could be a string URL or a list
        output = data.get("output")
        if isinstance(output, list):
            # Find first image URL in the output
            for item in output:
                if isinstance(item, str) and item.startswith("http"):
                    return item
            raise Exception(f"No image URL found in Replicate output: {output}")
        elif isinstance(output, str) and output.startswith("http"):
            return output
        else:
            raise Exception(f"Unexpected Replicate output format: {output}")


def extract_openrouter_image_data_url(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise Exception("OpenRouter image generation failed: no choices returned")

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")

    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            image_url = item.get("image_url")
            if isinstance(image_url, dict):
                url = image_url.get("url")
                if isinstance(url, str) and url.startswith("data:image/"):
                    return url
            if item.get("type") == "output_image" and isinstance(item.get("image_url"), str):
                url = item.get("image_url")
                if url.startswith("data:image/"):
                    return url
            if item.get("type") == "image" and isinstance(item.get("data"), str):
                data_url = item.get("data")
                if data_url.startswith("data:image/"):
                    return data_url

    raise Exception("OpenRouter image generation failed: no image content found in response")


async def call_openrouter_image(
    prompt: str,
    model: str,
    aspect_ratio: str,
    prompt_metadata: Optional[dict] = None,
) -> str:
    write_prompt_log(
        "image-generation",
        prompt,
        metadata={
            "provider": "openrouter",
            "model": model,
            "aspect_ratio": aspect_ratio,
            **(prompt_metadata or {}),
        },
    )
    payload = {
        "model": model,
        "modalities": ["image", "text"],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "image_config": {
            "aspect_ratio": aspect_ratio,
        },
    }

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Dementia Poster Generator",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return extract_openrouter_image_data_url(data)


async def download_image(url: str, filename: str, metadata: Optional[dict[str, str]] = None) -> Path:
    """Download an image from a URL and save it as a PNG with embedded metadata."""
    output_path = OUTPUT_DIR / filename
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
        )
        resp.raise_for_status()

    png_info = PngInfo()
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        png_info.add_text(key, str(value))

    with Image.open(BytesIO(resp.content)) as image:
        image.save(output_path, format="PNG", pnginfo=png_info)
    return output_path


def save_data_url_image(data_url: str, filename: str, metadata: Optional[dict[str, str]] = None) -> Path:
    if not data_url.startswith("data:image/"):
        raise Exception("OpenRouter image generation failed: invalid image data URL")

    try:
        _, encoded = data_url.split(",", 1)
    except ValueError as exc:
        raise Exception("OpenRouter image generation failed: malformed image data URL") from exc

    image_bytes = base64.b64decode(encoded)
    output_path = OUTPUT_DIR / filename
    png_info = PngInfo()
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        png_info.add_text(key, str(value))

    with Image.open(BytesIO(image_bytes)) as image:
        image.save(output_path, format="PNG", pnginfo=png_info)
    return output_path


def rewrite_png_metadata(path: Path, metadata: Optional[dict[str, str]] = None) -> Path:
    png_info = PngInfo()
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        png_info.add_text(key, str(value))

    with Image.open(path) as image:
        image.save(path, format="PNG", pnginfo=png_info)
    return path


def save_placeholder_output_image(
    filename: str,
    aspect_ratio: str,
    message: str,
    metadata: Optional[dict[str, str]] = None,
) -> Path:
    output_path = OUTPUT_DIR / filename
    placeholder_sizes = {
        "1:1": (1600, 1600),
        "3:4": (1500, 2000),
        "4:3": (2000, 1500),
        "9:16": (1125, 2000),
        "16:9": (2000, 1125),
    }
    width, height = placeholder_sizes.get(aspect_ratio, (1500, 2000))
    image = Image.new("RGB", (width, height), color="#f3efe9")
    draw = ImageDraw.Draw(image)
    title_font_size = max(28, min(width, height) // 18)
    footer_font_size = max(18, min(width, height) // 40)
    try:
        title_font = ImageFont.truetype("DejaVuSans.ttf", title_font_size)
        footer_font = ImageFont.truetype("DejaVuSans.ttf", footer_font_size)
    except Exception:
        title_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()

    border_margin = max(32, min(width, height) // 24)
    draw.rounded_rectangle(
        [(border_margin, border_margin), (width - border_margin, height - border_margin)],
        radius=max(24, min(width, height) // 30),
        outline="#c2714f",
        width=max(4, min(width, height) // 260),
        fill="#fffdfb",
    )

    lines = [
        "Image generation was disabled",
        "for this job when it was run.",
    ]
    line_gap = 18
    line_boxes = [draw.textbbox((0, 0), line, font=title_font) for line in lines]
    text_heights = [(box[3] - box[1]) for box in line_boxes]
    text_widths = [(box[2] - box[0]) for box in line_boxes]
    total_height = sum(text_heights) + line_gap * (len(lines) - 1)
    y = (height - total_height) / 2
    for index, line in enumerate(lines):
        line_width = text_widths[index]
        line_height = text_heights[index]
        x = (width - line_width) / 2
        draw.text((x, y), line, fill="#2c2520", font=title_font)
        y += line_height + line_gap

    if message.strip():
        footer = message.strip()
        footer_box = draw.textbbox((0, 0), footer, font=footer_font)
        footer_width = footer_box[2] - footer_box[0]
        footer_height = footer_box[3] - footer_box[1]
        footer_x = (width - footer_width) / 2
        footer_y = height - border_margin - footer_height - 24
        draw.text((footer_x, footer_y), footer, fill="#7a6e62", font=footer_font)

    png_info = PngInfo()
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        png_info.add_text(key, str(value))

    image.save(output_path, format="PNG", pnginfo=png_info)
    return output_path


async def save_generated_image(image_result: str, provider: str, filename: str, metadata: Optional[dict[str, str]] = None) -> Path:
    if provider == "replicate":
        return await download_image(image_result, filename, metadata)
    if provider == "openrouter":
        return save_data_url_image(image_result, filename, metadata)
    raise Exception(f"Unsupported image provider: {provider}")


def refresh_output_job_metadata(job_id: str, filename: str):
    path = resolve_output_image(filename)
    job = load_job(job_id)
    rewrite_png_metadata(path, build_png_job_metadata(job))


def refresh_all_job_output_metadata(job_id: str):
    job = load_job(job_id)
    for filename in [str(item) for item in (job.get("output_filenames") or []) if item]:
        try:
            rewrite_png_metadata(resolve_output_image(filename), build_png_job_metadata(job))
        except HTTPException:
            continue


def build_output_filename(pipeline_name: str, job_id: str, run_number: int, run_count: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    pipeline_slug = slugify(pipeline_name)
    job_slug = slugify(job_id)[:8] or "job"
    run_suffix = f"_r{run_number}" if run_count > 1 else ""
    return f"{timestamp}_{job_slug}_{pipeline_slug}{run_suffix}.png"


async def print_output(output_path: Path, job: dict) -> dict:
    settings_snapshot = job.get("settings_snapshot") or {}
    send_to_printer = bool(settings_snapshot.get("send_to_printer", False))
    printer_name = str(settings_snapshot.get("printer_name") or "").strip()
    print_orientation = str(settings_snapshot.get("print_orientation") or "portrait").strip()
    print_fit_mode = str(settings_snapshot.get("print_fit_mode") or "default").strip()
    if not send_to_printer or not printer_name:
        return {
            "print_status": "skipped",
            "printed_at": None,
            "print_error": None,
        }

    orientation_option = PRINT_ORIENTATIONS.get(print_orientation, PRINT_ORIENTATIONS["portrait"])
    fit_mode_option = PRINT_FIT_MODES.get(print_fit_mode, PRINT_FIT_MODES["default"])
    lp_args = [
        "lp",
        "-d",
        printer_name,
        *orientation_option["lp_options"],
        *fit_mode_option["lp_options"],
        str(output_path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *lp_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return {
            "print_status": "error",
            "printed_at": None,
            "print_error": "lp command not found",
        }
    stdout, stderr = await process.communicate()
    stdout_text = (stdout or b"").decode("utf-8", errors="replace").strip()
    stderr_text = (stderr or b"").decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        error_text = stderr_text or stdout_text or f"lp exited with code {process.returncode}"
        return {
            "print_status": "error",
            "printed_at": None,
            "print_error": error_text,
        }

    if stdout_text:
        log_event(
            "info",
            "Processing",
            f"Print queue accepted {output_path.name} via {printer_name}: {stdout_text}",
            filename=output_path.name,
            printer_name=printer_name,
        )

    return {
        "print_status": "printed",
        "printed_at": datetime.now().isoformat(),
        "print_error": None,
    }


# --- API Routes ---

@app.get("/api/images")
async def list_images():
    """List images currently in the watch folder."""
    files = get_image_files()
    result = []
    for f in files:
        b64 = image_to_base64(f)
        media_type = get_media_type(f)
        result.append({
            "filename": f.name,
            "data_url": f"data:{media_type};base64,{b64}",
        })
    return {"images": result}


@app.get("/api/prompts")
async def get_prompts():
    pipeline = load_pipeline(current_pipeline_id)
    return {
        "pipeline_id": pipeline["id"],
        "name": pipeline["name"],
        "interpretation": pipeline["interpretation"],
        "image": pipeline["image"],
        "path": pipeline["path"],
    }


@app.put("/api/prompts")
async def update_prompts(body: dict):
    global current_pipeline
    pipeline = save_pipeline(
        current_pipeline_id,
        body.get("name") or current_pipeline["name"],
        body.get("interpretation", current_pipeline["interpretation"]),
        body.get("image", current_pipeline["image"]),
    )
    current_pipeline = pipeline
    return {"ok": True, **pipeline}


@app.get("/api/pipelines")
async def get_pipelines():
    global current_pipeline
    current_pipeline = load_pipeline(current_pipeline_id)
    return {
        "items": list_pipeline_summaries(),
        "current_pipeline_id": current_pipeline_id,
        "default_pipeline_id": get_default_pipeline_id(),
    }


@app.get("/api/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    return load_pipeline(pipeline_id)


@app.get("/api/pipelines/{pipeline_id}/source")
async def get_pipeline_source(pipeline_id: str):
    path = resolve_pipeline_path(pipeline_id)

    return {
        "id": path.stem,
        "path": str(path),
        "content": path.read_text(),
    }


@app.post("/api/pipelines")
async def add_pipeline(body: dict):
    global current_pipeline_id, current_pipeline
    pipeline = create_pipeline((body or {}).get("name", ""))
    current_pipeline_id = pipeline["id"]
    current_pipeline = pipeline
    return {"ok": True, **pipeline}


@app.put("/api/pipelines/{pipeline_id}")
async def update_pipeline(pipeline_id: str, body: dict):
    global current_pipeline_id, current_pipeline
    pipeline = save_pipeline(
        pipeline_id,
        body.get("name") or pipeline_id.replace("-", " ").title(),
        body.get("interpretation", ""),
        body.get("image", ""),
    )
    current_pipeline_id = pipeline["id"]
    current_pipeline = pipeline
    return {"ok": True, **pipeline}


@app.put("/api/pipelines/{pipeline_id}/source")
async def update_pipeline_source(pipeline_id: str, body: dict):
    global current_pipeline_id, current_pipeline
    content = (body or {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "Pipeline Markdown content is required")

    path = resolve_pipeline_path(pipeline_id)

    parsed = parse_pipeline_markdown(content, path.stem)
    path.write_text(content)

    if current_pipeline_id == path.stem:
        current_pipeline = parsed

    return {
        "ok": True,
        "id": parsed["id"],
        "name": parsed["name"],
        "path": str(path),
        "content": content,
    }


@app.get("/api/settings")
async def get_settings():
    available_printers = list_available_printers()
    return {
        "default_pipeline_id": get_default_pipeline_id(),
        "available_pipeline_ids": list_viable_pipeline_ids(),
        "debug_mode": get_debug_mode(),
        "http_access_logging": get_http_access_logging(),
        "skip_image_generation": get_skip_image_generation(),
        "watcher_enabled": get_watcher_enabled(),
        "watched_folder": get_watched_folder_setting(),
        "text_model": get_text_model(),
        "available_text_models": [
            {"id": model_id, "label": option["label"]}
            for model_id, option in TEXT_MODELS.items()
        ],
        "image_model": get_default_image_model(),
        "available_image_models": [
            {"id": option_id, "label": option["label"]}
            for option_id, option in IMAGE_MODELS.items()
            if option["provider"] == "replicate"
        ],
        "aspect_ratio": get_default_aspect_ratio(),
        "run_count": get_default_run_count(),
        "encourage_variety_within_batches": get_encourage_variety_within_batches(),
        "encourage_variety_across_session": get_encourage_variety_across_session(),
        "variety_compression_prompt": get_variety_compression_prompt(),
        "printer_name": get_printer_name(),
        "send_to_printer": get_send_to_printer(),
        "available_printers": available_printers,
        "print_orientation": get_print_orientation(),
        "available_print_orientations": [
            {"id": option_id, "label": option["label"]}
            for option_id, option in PRINT_ORIENTATIONS.items()
        ],
        "print_fit_mode": get_print_fit_mode(),
        "available_print_fit_modes": [
            {"id": option_id, "label": option["label"]}
            for option_id, option in PRINT_FIT_MODES.items()
        ],
        "layout": get_layout_settings(),
    }


@app.get("/api/config/source")
async def get_config_source():
    return {
        "content": get_raw_config_content(),
        "default_content": serialize_config_json(get_default_config_template()),
    }


@app.put("/api/config/source")
async def update_config_source(body: dict):
    if pipeline_state["status"] not in ("idle", "complete", "cancelled", "error"):
        raise HTTPException(400, "Cannot edit config.json while a job is active")

    content = (body or {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "Config JSON content is required")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(400, "Config JSON must be an object")

    previous_encourage_variety_across_session = get_encourage_variety_across_session()
    previous_content = CONFIG_FILE.read_text() if CONFIG_FILE.exists() else None

    try:
        save_config(parsed)
        normalized = ensure_config()
    except Exception as exc:
        if previous_content is not None:
            CONFIG_FILE.write_text(previous_content)
        elif CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        raise HTTPException(400, str(exc)) from exc

    await apply_config_runtime_updates(previous_encourage_variety_across_session)
    log_event("info", "System", "config.json updated via editor")
    return {
        "ok": True,
        "content": get_raw_config_content(),
        "default_content": serialize_config_json(get_default_config_template()),
        "normalized": normalized,
    }


@app.post("/api/config/source/reset")
async def reset_config_source():
    if pipeline_state["status"] not in ("idle", "complete", "cancelled", "error"):
        raise HTTPException(400, "Cannot reset config.json while a job is active")

    previous_encourage_variety_across_session = get_encourage_variety_across_session()
    save_config(get_default_config_template())
    normalized = ensure_config()
    await apply_config_runtime_updates(previous_encourage_variety_across_session)
    log_event("info", "System", "config.json reset to built-in default")
    return {
        "ok": True,
        "content": get_raw_config_content(),
        "default_content": serialize_config_json(get_default_config_template()),
        "normalized": normalized,
    }


@app.put("/api/settings")
async def update_settings(body: dict):
    pipeline_id = (body or {}).get("default_pipeline_id")
    viable_ids = list_viable_pipeline_ids()
    if pipeline_id not in viable_ids:
        raise HTTPException(400, "Invalid default pipeline")

    requested_layout = (body or {}).get("layout") or {}
    available_printers = list_available_printers()
    requested_printer_name = str((body or {}).get("printer_name") or "").strip()
    requested_send_to_printer = bool((body or {}).get("send_to_printer", False))
    current_printer_name = get_printer_name()
    if requested_printer_name and requested_printer_name not in available_printers and requested_printer_name != current_printer_name:
        raise HTTPException(400, "Invalid printer")
    requested_print_orientation = str((body or {}).get("print_orientation") or "portrait").strip()
    if requested_print_orientation not in PRINT_ORIENTATIONS:
        raise HTTPException(400, "Invalid print orientation")
    requested_print_fit_mode = str((body or {}).get("print_fit_mode") or "default").strip()
    if requested_print_fit_mode not in PRINT_FIT_MODES:
        raise HTTPException(400, "Invalid print fit mode")
    requested_image_model = (
        (body or {}).get("image_model")
        if (body or {}).get("image_model") in IMAGE_MODELS
        else get_default_image_model()
    )
    requested_aspect_ratio = str((body or {}).get("aspect_ratio") or get_default_aspect_ratio()).strip()
    if requested_aspect_ratio not in ASPECT_RATIOS:
        raise HTTPException(400, "Invalid aspect ratio")
    if requested_aspect_ratio not in get_allowed_aspect_ratios(requested_image_model):
        raise HTTPException(400, "Aspect ratio is not supported for the selected image model")
    requested_run_count = int((body or {}).get("run_count") or get_default_run_count())
    if requested_run_count < 1 or requested_run_count > 20:
        raise HTTPException(400, "Run count must be between 1 and 20")
    requested_watcher_enabled = bool((body or {}).get("watcher_enabled", True))
    requested_watched_folder = str((body or {}).get("watched_folder") or get_watched_folder_setting()).strip() or "watch/"
    try:
        resolved_watch_dir = resolve_watched_folder_path(requested_watched_folder)
    except Exception as exc:
        raise HTTPException(400, f"Invalid watched folder: {exc}") from exc
    requested_encourage_variety_within_batches = bool((body or {}).get("encourage_variety_within_batches", False))
    requested_encourage_variety_across_session = bool((body or {}).get("encourage_variety_across_session", False))
    previous_encourage_variety_across_session = get_encourage_variety_across_session()
    content_row_height = requested_layout.get("content_row_height", get_layout_settings().get("content_row_height", 448))
    if not isinstance(content_row_height, (int, float)):
        content_row_height = get_layout_settings().get("content_row_height", 448)
    content_row_height = max(220, min(1200, int(content_row_height)))

    save_config({
        "default_pipeline_id": pipeline_id,
        "debug_mode": bool((body or {}).get("debug_mode", False)),
        "http_access_logging": bool((body or {}).get("http_access_logging", False)),
        "skip_image_generation": bool((body or {}).get("skip_image_generation", False)),
        "watcher_enabled": requested_watcher_enabled,
        "watched_folder": requested_watched_folder,
        "text_model": (body or {}).get("text_model")
        if (body or {}).get("text_model") in TEXT_MODELS
        else get_text_model(),
        "image_model": requested_image_model,
        "aspect_ratio": requested_aspect_ratio,
        "run_count": requested_run_count,
        "encourage_variety_within_batches": requested_encourage_variety_within_batches,
        "encourage_variety_across_session": requested_encourage_variety_across_session,
        "variety_compression_prompt": str((body or {}).get("variety_compression_prompt") or get_variety_compression_prompt()),
        "printer_name": requested_printer_name,
        "send_to_printer": requested_send_to_printer,
        "print_orientation": requested_print_orientation,
        "print_fit_mode": requested_print_fit_mode,
        "layout": {
            "content_row_height": content_row_height,
        },
    })
    pipeline_state["image_model"] = get_default_image_model()
    pipeline_state["aspect_ratio"] = get_default_aspect_ratio()
    pipeline_state["send_to_printer"] = get_send_to_printer()
    pipeline_state["run_count"] = get_default_run_count()
    pipeline_state["encourage_variety_within_batches"] = get_encourage_variety_within_batches()
    pipeline_state["encourage_variety_across_session"] = get_encourage_variety_across_session()
    if requested_encourage_variety_across_session and not previous_encourage_variety_across_session:
        clear_session_variety_state()
        log_event("info", "System", "Session variety memory reset because across-session variety was enabled")
    await sync_watcher_state(
        f"Automatic watch processing {'enabled' if requested_watcher_enabled else 'disabled'} for {resolved_watch_dir}",
        force_restart=True,
    )
    log_event(
        "info",
        "System",
        "Settings updated",
        pipeline_id=pipeline_id,
        printer_name=requested_printer_name or None,
    )

    return {
        "ok": True,
        "default_pipeline_id": get_default_pipeline_id(),
        "debug_mode": get_debug_mode(),
        "http_access_logging": get_http_access_logging(),
        "skip_image_generation": get_skip_image_generation(),
        "watcher_enabled": get_watcher_enabled(),
        "watched_folder": get_watched_folder_setting(),
        "text_model": get_text_model(),
        "image_model": get_default_image_model(),
        "aspect_ratio": get_default_aspect_ratio(),
        "run_count": get_default_run_count(),
        "encourage_variety_within_batches": get_encourage_variety_within_batches(),
        "encourage_variety_across_session": get_encourage_variety_across_session(),
        "variety_compression_prompt": get_variety_compression_prompt(),
        "printer_name": get_printer_name(),
        "send_to_printer": get_send_to_printer(),
        "available_printers": available_printers,
        "print_orientation": get_print_orientation(),
        "available_print_orientations": [
            {"id": option_id, "label": option["label"]}
            for option_id, option in PRINT_ORIENTATIONS.items()
        ],
        "print_fit_mode": get_print_fit_mode(),
        "available_print_fit_modes": [
            {"id": option_id, "label": option["label"]}
            for option_id, option in PRINT_FIT_MODES.items()
        ],
        "layout": get_layout_settings(),
    }


@app.get("/api/errors")
async def get_errors():
    return {"items": runtime_errors}


@app.get("/api/system/log")
async def get_system_log():
    return {"items": system_events}


@app.delete("/api/system/log")
async def clear_system_log():
    system_events.clear()
    runtime_errors.clear()
    return {"ok": True}


@app.post("/api/errors")
async def add_error(body: dict):
    message = (body or {}).get("message", "").strip()
    source = (body or {}).get("source", "client").strip() or "client"
    if source == "client":
        source = "Browser"
    if not message:
        raise HTTPException(400, "No error message provided")

    log_error(message, source)
    return {"ok": True}


@app.delete("/api/errors")
async def clear_errors():
    runtime_errors.clear()
    return {"ok": True}


@app.post("/api/capture")
async def capture_image(body: dict):
    data_url = body.get("image")
    if not data_url:
        raise HTTPException(400, "No image provided")

    filename = save_base64_image(data_url)
    return {"ok": True, "filename": filename}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    filename = await save_uploaded_image(file)
    return {"ok": True, "filename": filename}


@app.delete("/api/images/{filename}")
async def delete_image(filename: str):
    path = resolve_watch_image(filename)
    path.unlink()
    return {"ok": True, "filename": filename}


@app.get("/api/watch/{filename}")
async def get_watch_image(filename: str):
    path = resolve_watch_image(filename)
    return FileResponse(path)


@app.get("/api/status")
async def get_status():
    return pipeline_state


@app.get("/api/system/status")
async def get_system_status():
    active_job = None
    job_id = pipeline_state.get("job_id")
    if job_id:
        try:
            job = load_job(job_id)
            active_job = {
                "id": job.get("id"),
                "status": job.get("status"),
                "trigger": job.get("trigger"),
                "pipeline_name": job.get("pipeline_name"),
                "source_images": job.get("source_images") or [],
                "message": job.get("message"),
            }
        except HTTPException:
            active_job = None

    return {
        "watcher_enabled": get_watcher_enabled(),
        "watched_folder": str(get_watch_dir()),
        "watcher_running": watcher_task is not None and not watcher_task.done(),
        "queue_worker_running": queue_worker_task is not None and not queue_worker_task.done(),
        "queue_length": job_queue.qsize() if job_queue is not None else 0,
        "pending_watch_candidates": len(pending_watch_candidates),
        "queued_watch_files": sorted(queued_watch_files),
        "active_job": active_job,
    }


@app.post("/api/watched-folder/pick")
async def pick_watched_folder():
    initial_path = get_watch_dir()
    selected = await choose_folder_via_dialog(initial_path)
    if not selected:
        return {"ok": True, "cancelled": True}
    resolved = resolve_watched_folder_path(selected)
    return {
        "ok": True,
        "cancelled": False,
        "watched_folder": str(resolved),
    }


@app.put("/api/run-config")
async def update_run_config(body: dict):
    global current_pipeline_id, current_pipeline
    if pipeline_state["status"] not in ("idle", "complete", "cancelled", "error"):
        raise HTTPException(400, "Cannot update run configuration while a job is active")

    body = body or {}
    pipeline_id = body.get("pipeline_id") or current_pipeline_id or get_default_pipeline_id()
    if pipeline_id not in list_viable_pipeline_ids():
        raise HTTPException(400, "Invalid pipeline")

    image_model = str(body.get("image_model") or get_default_image_model()).strip()
    if image_model not in IMAGE_MODELS:
        raise HTTPException(400, "Invalid image model")

    aspect_ratio = str(body.get("aspect_ratio") or get_default_aspect_ratio()).strip()
    if aspect_ratio not in ASPECT_RATIOS:
        raise HTTPException(400, "Invalid aspect ratio")
    if aspect_ratio not in get_allowed_aspect_ratios(image_model):
        raise HTTPException(400, "Aspect ratio is not supported for the selected image model")

    run_count = int(body.get("run_count") or get_default_run_count())
    if run_count < 1 or run_count > 20:
        raise HTTPException(400, "Run count must be between 1 and 20")

    encourage_variety_within_batches = bool(body.get("encourage_variety_within_batches", False))
    previous_encourage_variety_across_session = bool(pipeline_state.get("encourage_variety_across_session", False))
    encourage_variety_across_session = bool(body.get("encourage_variety_across_session", False))

    current_pipeline_id = pipeline_id
    current_pipeline = load_pipeline(pipeline_id)
    pipeline_state["pipeline_id"] = pipeline_id
    pipeline_state["image_model"] = image_model
    pipeline_state["aspect_ratio"] = aspect_ratio
    pipeline_state["run_count"] = run_count
    pipeline_state["encourage_variety_within_batches"] = encourage_variety_within_batches
    pipeline_state["encourage_variety_across_session"] = encourage_variety_across_session
    if encourage_variety_across_session and not previous_encourage_variety_across_session:
        clear_session_variety_state()
        log_event("info", "System", "Session variety memory reset because across-session variety was enabled")

    return {
        "ok": True,
        **get_current_run_config(),
    }


@app.get("/api/jobs")
async def get_jobs():
    return {"items": list_jobs()}


@app.get("/api/queue")
async def get_queue_status():
    return get_queue_status_payload()


@app.delete("/api/queue/{job_id}")
async def remove_queued_job(job_id: str):
    global job_queue
    if job_queue is None:
        raise HTTPException(400, "Job queue is not initialized")

    raw_items = list(getattr(job_queue, "_queue", []))
    remaining_items = []
    removed_item = None
    for item in raw_items:
        if removed_item is None and isinstance(item, dict) and str(item.get("job_id") or "") == job_id:
            removed_item = item
            continue
        remaining_items.append(item)

    if removed_item is None:
        raise HTTPException(404, "Queued job not found")

    queue_data = getattr(job_queue, "_queue", None)
    if queue_data is None:
        raise HTTPException(500, "Queue internals unavailable")
    queue_data.clear()
    queue_data.extend(remaining_items)

    filename = str(removed_item.get("filename") or "").strip()
    if filename:
        queued_watch_files.discard(filename)

    update_job(
        job_id,
        status="cancelled",
        completed_at=datetime.now().isoformat(),
        message="Removed from queue",
    )
    log_queue_length_change("job removed from queue")
    log_event("info", "Jobs", f"Removed queued job {job_id}", job_id=job_id, filename=filename or None)
    return {"ok": True, **get_queue_status_payload()}


@app.post("/api/queue/restart")
async def restart_queue_worker():
    global queue_worker_current_item
    preserved_item = dict(queue_worker_current_item) if isinstance(queue_worker_current_item, dict) else None
    active_processing_job_id = pipeline_state.get("job_id") if pipeline_state.get("status") in ("interpreting", "generating", "downloading", "printing", "cancelling") else None

    await stop_queue_worker(reset_queue=False)

    if (
        preserved_item
        and job_queue is not None
        and str(preserved_item.get("job_id") or "") != str(active_processing_job_id or "")
    ):
        preserved_job_id = str(preserved_item.get("job_id") or "").strip()
        if preserved_job_id:
            try:
                load_job(preserved_job_id)
                await job_queue.put(preserved_item)
                log_queue_length_change("queue worker restarted and preserved claimed item")
            except HTTPException as exc:
                if exc.status_code == 404:
                    log_event(
                        "warning",
                        "System",
                        f"Dropped stale claimed job {preserved_job_id} during queue restart because its job file was not found",
                        job_id=preserved_job_id,
                        filename=str(preserved_item.get("filename") or "").strip() or None,
                    )
                else:
                    raise
        else:
            await job_queue.put(preserved_item)
            log_queue_length_change("queue worker restarted and preserved claimed item")

    await start_queue_worker("Queue worker restarted")
    return {"ok": True, **get_queue_status_payload()}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    return load_job(job_id)


@app.post("/api/jobs/{job_id}/reprint")
async def reprint_job(job_id: str):
    job = load_job(job_id)
    output_filename = str(job.get("output_filename") or "").strip()
    if not output_filename:
        raise HTTPException(400, "Job has no generated output to reprint")

    output_path = resolve_output_image(output_filename)

    log_event(
        "info",
        "Processing",
        f"Sending saved output to print queue: {output_filename}",
        job_id=job_id,
        filename=output_filename,
    )
    print_result = await print_output(output_path, job)
    update_job(job_id, **print_result)

    if print_result["print_status"] == "error":
        error_text = print_result.get("print_error") or "Unknown print handoff error"
        update_job(job_id, message=f"Reprint failed: {error_text}")
        log_error(
            f"Reprint handoff failed for job {job_id} ({output_filename}): {error_text}",
            "Processing",
        )
        raise HTTPException(500, error_text)

    if print_result["print_status"] == "printed":
        update_job(job_id, message="Saved output sent to print queue")
        log_event(
            "info",
            "Processing",
            f"Saved output sent to print queue: {output_filename}",
            job_id=job_id,
            filename=output_filename,
        )
    else:
        update_job(job_id, message="Reprint skipped")
        log_event(
            "info",
            "Processing",
            f"Reprint skipped for saved output: {output_filename}",
            job_id=job_id,
            filename=output_filename,
        )

    refreshed_job = load_job(job_id)
    return {
        "ok": True,
        "job": refreshed_job,
    }


@app.post("/api/jobs/{job_id}/requeue")
async def requeue_job(job_id: str):
    job = load_job(job_id)
    source_images = [name for name in (job.get("source_images") or []) if isinstance(name, str) and name.strip()]
    if not source_images:
        raise HTTPException(400, "Job has no source images to requeue")

    copied_filenames = requeue_watch_images(source_images)
    log_event(
        "info",
        "Watch Folder",
        f"Requeued {len(copied_filenames)} source image(s) from job {job_id}",
        job_id=job_id,
    )
    return {
        "ok": True,
        "filenames": copied_filenames,
    }


@app.post("/api/jobs/{job_id}/feedback")
async def feedback_job(job_id: str):
    job = load_job(job_id)
    output_filename = str(job.get("output_filename") or "").strip()
    if not output_filename:
        raise HTTPException(400, "Job has no generated output to feed back")

    copied_filename = copy_output_image_to_watch(output_filename, "feedback")
    log_event(
        "info",
        "Watch Folder",
        f"Fed back generated output from job {job_id} into watch folder",
        job_id=job_id,
        filename=copied_filename,
    )
    return {
        "ok": True,
        "filename": copied_filename,
    }


@app.post("/api/cancel")
async def cancel_pipeline():
    global pipeline_task
    if pipeline_state["status"] not in ("interpreting", "generating", "downloading", "printing") or pipeline_task is None:
        raise HTTPException(400, "No active pipeline to cancel")

    pipeline_state["cancel_requested"] = True
    pipeline_state["status"] = "cancelling"
    pipeline_state["message"] = "Cancelling current batch..."
    if pipeline_state.get("job_id"):
        update_job(
            pipeline_state["job_id"],
            status="cancelling",
            message="Cancelling current batch...",
        )
    pipeline_task.cancel()
    return {"ok": True, "status": "cancelling"}


@app.post("/api/meaningful-difference/clear")
async def clear_meaningful_difference():
    if pipeline_state["status"] in ("interpreting", "generating", "downloading", "printing", "cancelling"):
        raise HTTPException(400, "Cannot clear session variety memory while pipeline is running")

    clear_session_variety_state()
    log_event("info", "System", "Session variety memory cleared")
    return {"ok": True}


@app.get("/api/results")
async def get_results():
    return {
        "description": pipeline_state.get("description"),
        "poster_filename": pipeline_state.get("poster_filename"),
        "source_images": pipeline_state.get("source_images", []),
        "pipeline_id": pipeline_state.get("pipeline_id"),
    }


@app.get("/api/library")
async def get_library():
    return {"items": build_library_index()}


@app.get("/api/library/export")
async def export_library():
    fd, temp_path = tempfile.mkstemp(prefix="library_export_", suffix=".zip")
    os.close(fd)
    archive_path = Path(temp_path)

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for path, arcname in iter_library_archive_files():
            archive.write(path, arcname=arcname)

    filename = f"library_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@app.post("/api/library/import")
async def import_library(file: UploadFile = File(...)):
    active_statuses = {"extracting_concepts", "interpreting", "generating", "downloading", "printing", "cancelling"}
    if pipeline_state.get("status") in active_statuses:
        raise HTTPException(400, "Cannot import while a job is actively processing")

    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Upload a zip file")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Uploaded zip is empty")

    try:
        with ZipFile(BytesIO(contents)) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
    except BadZipFile as exc:
        raise HTTPException(400, "Invalid zip file") from exc

    imported = 0
    import_succeeded = False
    try:
        await stop_watcher("Watcher paused for library import")
        await stop_queue_worker("Queue worker paused for library import", reset_queue=True)

        for directory in get_library_archive_directories().values():
            clear_directory_contents(directory)

        with ZipFile(BytesIO(contents)) as archive:
            for member in members:
                target = resolve_library_import_target(member.filename)
                if target is None:
                    continue
                with archive.open(member) as source, open(target, "wb") as destination:
                    destination.write(source.read())
                imported += 1
        import_succeeded = True
        pipeline_state.update({
            "job_id": None,
            "status": "idle",
            "message": "Import complete",
            "description": None,
            "poster_filename": None,
            "poster_filenames": [],
            "error": None,
            "started_at": None,
            "source_images": [],
            "completed_runs": 0,
            "current_run": 0,
            "job_interpretation_history": [],
            "job_variety_text": "",
            "variety_guidance_text": pipeline_state.get("session_variety_text") or "",
            "meaningful_difference_text": pipeline_state.get("session_variety_text") or "",
            "extracted_concepts": "",
            "cancel_requested": False,
        })
        log_event("info", "System", f"Library import restored {imported} file{'s' if imported != 1 else ''}")
    finally:
        await start_queue_worker("Queue worker restarted after library import")
        await sync_watcher_state("Watch folder baseline reset after library import", force_restart=True)

    if not import_succeeded:
        raise HTTPException(500, "Library import failed")

    return {"ok": True, "imported": imported}


@app.post("/api/run")
async def run_pipeline(body: dict):
    """Trigger the full pipeline."""
    global pipeline_task
    if pipeline_state["status"] not in ("idle", "complete", "cancelled", "error"):
        raise HTTPException(400, "Pipeline is already running")

    selected_filenames = body.get("filenames") if body else None
    pipeline_id = body.get("pipeline_id") if body else None
    interpretation_prompt = (body.get("interpretation_prompt") or "").strip() if body else ""
    image_generation_prompt = (body.get("image_generation_prompt") or "").strip() if body else ""
    image_model = (body.get("image_model") or get_default_image_model()).strip() if body else get_default_image_model()
    aspect_ratio = (body.get("aspect_ratio") or get_default_aspect_ratio()).strip() if body else get_default_aspect_ratio()
    run_count = int((body.get("run_count") or get_default_run_count())) if body else get_default_run_count()
    encourage_variety_within_batches = bool((body.get("encourage_variety_within_batches") or False)) if body else False
    encourage_variety_across_session = bool((body.get("encourage_variety_across_session") or False)) if body else False
    if not isinstance(selected_filenames, list) or not selected_filenames:
        raise HTTPException(400, "No images selected")
    if not pipeline_id:
        raise HTTPException(400, "No pipeline selected")
    image_model_option = get_image_model_option(image_model)
    if aspect_ratio not in ASPECT_RATIOS:
        raise HTTPException(400, "Invalid aspect ratio")
    if aspect_ratio not in get_allowed_aspect_ratios(image_model):
        raise HTTPException(400, "Aspect ratio is not supported for the selected image model")
    if run_count < 1 or run_count > 20:
        raise HTTPException(400, "Run count must be between 1 and 20")

    effective_rerun_interpretation = run_count > 1
    images = resolve_selected_images(selected_filenames)
    pipeline = load_pipeline(pipeline_id)
    if interpretation_prompt:
        pipeline["interpretation"] = interpretation_prompt
    if image_generation_prompt:
        pipeline["image"] = image_generation_prompt

    job = create_job(
        trigger="manual",
        source_images=selected_filenames,
        pipeline=pipeline,
        text_model=get_text_model(),
        image_model=image_model,
        printer_name=get_printer_name(),
        send_to_printer=get_send_to_printer(),
        print_orientation=get_print_orientation(),
        print_fit_mode=get_print_fit_mode(),
        aspect_ratio=aspect_ratio,
        run_count=run_count,
        encourage_variety_within_batches=encourage_variety_within_batches,
        encourage_variety_across_session=encourage_variety_across_session,
        skip_image_generation=get_skip_image_generation(),
    )
    launch_pipeline_job(job, images, pipeline, image_model_option)

    return {
        "ok": True,
        "job_id": job["id"],
        "status": "interpreting",
        "image_count": len(images),
        "run_count": run_count,
    }

async def _run_pipeline(
    job_id: str,
    images: list[Path],
    pipeline: dict,
    image_model_option: dict,
    aspect_ratio: str,
    run_count: int,
    rerun_interpretation: bool,
    encourage_variety_within_batches: bool,
    encourage_variety_across_session: bool,
):
    """Run interpretation and generation end-to-end."""
    global pipeline_task
    try:
        description = None
        job_interpretation_history: list[str] = list(pipeline_state.get("job_interpretation_history") or [])
        session_interpretation_history: list[str] = list(pipeline_state.get("session_interpretation_history") or [])
        batch_variety_text = pipeline_state.get("job_variety_text") or ""
        session_variety_text = pipeline_state.get("session_variety_text") or ""
        extracted_concepts = ""
        resolved_interpretation_prompt = ""
        image_prompt = ""
        skip_image_generation = get_skip_image_generation()
        generation_started_at_iso = None
        generation_estimate_seconds = None

        update_job(
            job_id,
            started_at=datetime.now().isoformat(),
            status="extracting_concepts",
            message=f"Extracting concepts from {len(images)} source image(s)...",
            pipeline_id=pipeline["id"],
            pipeline_name=pipeline["name"],
        )
        log_event(
            "info",
            "Processing",
            "\n".join([
                "Processing started",
                f"Job ID: {job_id}",
                f"Pipeline: {pipeline['name']}",
                f"Source images: {len(images)}",
            ]),
            job_id=job_id,
            pipeline_id=pipeline["id"],
        )
        pipeline_state["status"] = "interpreting"
        pipeline_state["message"] = f"Extracting concepts from {len(images)} source image(s)..."
        extracted_concepts = await call_claude(
            images,
            EXTRACTED_CONCEPTS_PROMPT,
            pipeline_name="Extracted Concepts",
            run_number=0,
            job_id=job_id,
            prompt_kind="concept-extraction",
        )
        extracted_concepts = require_extracted_concepts(extracted_concepts)
        pipeline_state["extracted_concepts"] = extracted_concepts
        update_job(
            job_id,
            status="interpreting",
            extracted_concepts=extracted_concepts,
            message="Extracted concepts",
        )
        log_event("info", "Processing", "Concept extraction complete", job_id=job_id, pipeline_id=pipeline["id"])

        for run_index in range(run_count):
            active_pipeline = pipeline
            pipeline_state["pipeline_id"] = active_pipeline["id"]
            pipeline_state["current_run"] = run_index + 1
            update_job(
                job_id,
                pipeline_id=active_pipeline["id"],
                pipeline_name=active_pipeline["name"],
                status="interpreting",
                message=f"Preparing run {run_index + 1} of {run_count}",
            )
            if run_index == 0 or rerun_interpretation:
                pipeline_state["status"] = "interpreting"
                batch_variety_text = ""
                session_variety_text = (
                    pipeline_state.get("session_variety_text") or ""
                    if encourage_variety_across_session
                    else ""
                )
                if encourage_variety_within_batches and run_count > 1 and job_interpretation_history:
                    pipeline_state["message"] = (
                        f"Updating batch variety guidance for run {run_index + 1} of {run_count}..."
                    )
                    batch_variety_text = await compress_meaningful_difference(
                        job_interpretation_history,
                        active_pipeline["name"],
                        run_index + 1,
                        job_id=job_id,
                    )
                else:
                    batch_variety_text = ""
                if not encourage_variety_across_session:
                    session_variety_text = ""
                resolved_interpretation_prompt = build_variety_guidance_prompt(
                    active_pipeline["interpretation"],
                    extracted_concepts=extracted_concepts,
                    batch_variety_text=batch_variety_text,
                    session_variety_text=session_variety_text,
                )
                variety_guidance_text = "\n\n".join(part for part in [batch_variety_text.strip(), session_variety_text.strip()] if part).strip()
                pipeline_state["job_variety_text"] = batch_variety_text
                pipeline_state["session_variety_text"] = session_variety_text
                pipeline_state["variety_guidance_text"] = variety_guidance_text
                pipeline_state["meaningful_difference_text"] = variety_guidance_text
                update_job(
                    job_id,
                    status="interpreting",
                    batch_variety_text=batch_variety_text,
                    session_variety_text=session_variety_text,
                    variety_guidance_text=variety_guidance_text,
                    meaningful_difference_text=variety_guidance_text,
                    resolved_interpretation_prompt=resolved_interpretation_prompt,
                    message=pipeline_state["message"],
                )
                if run_count > 1 and rerun_interpretation:
                    pipeline_state["message"] = (
                        f"Creating intermediate prompt for run {run_index + 1} of {run_count} with {active_pipeline['name']}..."
                    )
                else:
                    pipeline_state["message"] = f"Creating intermediate prompt for run {run_index + 1} with {active_pipeline['name']}..."
                update_job(job_id, status="interpreting", message=pipeline_state["message"])
                log_event("info", "Processing", pipeline_state["message"], job_id=job_id, pipeline_id=active_pipeline["id"])
                description = await call_claude(
                    [],
                    resolved_interpretation_prompt,
                    pipeline_name=active_pipeline["name"],
                    run_number=run_index + 1,
                    job_id=job_id,
                    encourage_variety=encourage_variety_within_batches or encourage_variety_across_session,
                    previous_interpretations=job_interpretation_history + session_interpretation_history,
                    meaningful_difference_text=variety_guidance_text,
                    prompt_kind="intermediate-prompt",
                )
                description = require_description(description, active_pipeline["name"], run_index + 1)
                pipeline_state["description"] = description
                job_interpretation_history.append(description)
                if encourage_variety_across_session:
                    session_interpretation_history.append(description)
                pipeline_state["job_interpretation_history"] = list(job_interpretation_history)
                pipeline_state["session_interpretation_history"] = list(session_interpretation_history)
                update_job(
                    job_id,
                    intermediate_prompt=description,
                    batch_variety_text=batch_variety_text,
                    session_variety_text=session_variety_text,
                    variety_guidance_text=variety_guidance_text,
                    meaningful_difference_text=variety_guidance_text,
                    resolved_interpretation_prompt=resolved_interpretation_prompt,
                    message=f"Created intermediate prompt for run {run_index + 1} of {run_count}",
                )
                log_event("info", "Processing", f"Intermediate prompt created for run {run_index + 1} of {run_count}", job_id=job_id, pipeline_id=active_pipeline["id"])

            description = require_description(description, active_pipeline["name"], run_index + 1)

            image_prompt = active_pipeline["image"].replace("{description}", description or "")
            if skip_image_generation:
                pipeline_state["status"] = "generating"
                pipeline_state["message"] = (
                    f"Skipped image generation for run {run_index + 1} of {run_count}."
                )
                pipeline_state["completed_runs"] = run_index + 1
                write_prompt_log(
                    "image-generation-skipped",
                    image_prompt,
                    metadata={
                        "pipeline_id": active_pipeline["id"],
                        "pipeline_name": active_pipeline["name"],
                        "job_id": job_id,
                        "run_number": run_index + 1,
                        "run_count": run_count,
                        "image_model": pipeline_state["image_model"],
                        "aspect_ratio": aspect_ratio,
                    },
                )
                filename = build_output_filename(
                    active_pipeline["name"],
                    job_id,
                    run_index + 1,
                    run_count,
                )
                job_with_output = normalize_job({
                    **load_job(job_id),
                    "output_filename": filename,
                    "output_filenames": list((load_job(job_id).get("output_filenames") or [])) + [filename],
                })
                output_path = save_placeholder_output_image(
                    filename,
                    aspect_ratio,
                    "Placeholder output created because image generation was disabled.",
                    metadata=build_png_job_metadata(job_with_output),
                )
                pipeline_state["poster_filename"] = filename
                pipeline_state["poster_filenames"].append(filename)
                current_job = load_job(job_id)
                output_filenames = list(current_job.get("output_filenames") or [])
                output_filenames.append(filename)
                update_job(
                    job_id,
                    status="complete" if run_index + 1 == run_count else "generating",
                    intermediate_prompt=description,
                    batch_variety_text=batch_variety_text,
                    session_variety_text=session_variety_text,
                    variety_guidance_text=variety_guidance_text,
                    meaningful_difference_text=variety_guidance_text,
                    resolved_interpretation_prompt=resolved_interpretation_prompt,
                    resolved_image_prompt=image_prompt,
                    output_filename=filename,
                    output_filenames=output_filenames,
                    print_status="skipped",
                    printed_at=None,
                    print_error=None,
                    generation_started_at=None,
                    generation_estimate_seconds=None,
                    generation_last_duration_seconds=None,
                    completed_at=datetime.now().isoformat() if run_index + 1 == run_count else None,
                    message=f"Placeholder output image saved for run {run_index + 1} of {run_count}",
                )
                refresh_output_job_metadata(job_id, filename)
                log_event("info", "Processing", f"Placeholder output image saved: {filename}", job_id=job_id, pipeline_id=active_pipeline["id"], filename=filename)
                continue
            pipeline_state["status"] = "generating"
            generation_estimate_seconds = get_image_generation_estimate_seconds()
            generation_started_at_iso = datetime.now().isoformat()
            pipeline_state["generation_started_at"] = generation_started_at_iso
            pipeline_state["generation_estimate_seconds"] = generation_estimate_seconds
            pipeline_state["message"] = (
                f"Generating image {run_index + 1} of {run_count} with {active_pipeline['name']} via {image_model_option['label']}..."
            )
            update_job(
                job_id,
                status="generating",
                message=pipeline_state["message"],
                generation_started_at=generation_started_at_iso,
                generation_estimate_seconds=generation_estimate_seconds,
                generation_last_duration_seconds=None,
                intermediate_prompt=description,
                batch_variety_text=batch_variety_text,
                session_variety_text=session_variety_text,
                variety_guidance_text=variety_guidance_text,
                meaningful_difference_text=variety_guidance_text,
                resolved_interpretation_prompt=resolved_interpretation_prompt,
                resolved_image_prompt=image_prompt,
            )
            log_event("info", "Processing", pipeline_state["message"], job_id=job_id, pipeline_id=active_pipeline["id"])
            if image_model_option["provider"] == "replicate":
                image_result = await call_replicate(
                    image_prompt,
                    image_model_option["model"],
                    aspect_ratio,
                    prompt_metadata={
                        "pipeline_id": active_pipeline["id"],
                        "pipeline_name": active_pipeline["name"],
                        "job_id": job_id,
                        "run_number": run_index + 1,
                        "run_count": run_count,
                        "image_model": pipeline_state["image_model"],
                    },
                )
            else:
                image_result = await call_openrouter_image(
                    image_prompt,
                    image_model_option["model"],
                    aspect_ratio,
                    prompt_metadata={
                        "pipeline_id": active_pipeline["id"],
                        "pipeline_name": active_pipeline["name"],
                        "job_id": job_id,
                        "run_number": run_index + 1,
                        "run_count": run_count,
                        "image_model": pipeline_state["image_model"],
                    },
                )

            if generation_started_at_iso:
                generation_duration_seconds = max(
                    0.0,
                    (datetime.now() - datetime.fromisoformat(generation_started_at_iso)).total_seconds(),
                )
                image_generation_duration_seconds_history.append(generation_duration_seconds)
                pipeline_state["generation_started_at"] = None
                pipeline_state["generation_estimate_seconds"] = None
                pipeline_state["generation_last_duration_seconds"] = generation_duration_seconds
            else:
                generation_duration_seconds = None

            pipeline_state["status"] = "downloading"
            pipeline_state["message"] = f"Saving output image {run_index + 1} of {run_count}..."
            update_job(
                job_id,
                status="downloading",
                message=pipeline_state["message"],
                generation_started_at=None,
                generation_estimate_seconds=generation_estimate_seconds,
                generation_last_duration_seconds=generation_duration_seconds,
            )
            log_event("info", "Processing", pipeline_state["message"], job_id=job_id, pipeline_id=active_pipeline["id"])

            filename = build_output_filename(
                active_pipeline["name"],
                job_id,
                run_index + 1,
                run_count,
            )
            output_path = await save_generated_image(
                image_result,
                image_model_option["provider"],
                filename,
                metadata=build_png_job_metadata(normalize_job({
                    **load_job(job_id),
                    "output_filename": filename,
                    "output_filenames": list((load_job(job_id).get("output_filenames") or [])) + [filename],
                })),
            )

            pipeline_state["poster_filename"] = filename
            pipeline_state["poster_filenames"].append(filename)
            pipeline_state["completed_runs"] = run_index + 1
            current_job = load_job(job_id)
            output_filenames = list(current_job.get("output_filenames") or [])
            output_filenames.append(filename)
            update_job(
                job_id,
                output_filename=filename,
                output_filenames=output_filenames,
                generation_started_at=None,
                generation_estimate_seconds=generation_estimate_seconds,
                generation_last_duration_seconds=generation_duration_seconds,
                intermediate_prompt=description,
                batch_variety_text=batch_variety_text,
                session_variety_text=session_variety_text,
                variety_guidance_text=variety_guidance_text,
                meaningful_difference_text=variety_guidance_text,
                resolved_interpretation_prompt=resolved_interpretation_prompt,
                resolved_image_prompt=image_prompt,
                message=f"Output image saved for run {run_index + 1} of {run_count}",
            )
            refresh_output_job_metadata(job_id, filename)
            log_event("info", "Processing", f"Output image saved: {filename}", job_id=job_id, pipeline_id=active_pipeline["id"], filename=filename)

            pipeline_state["status"] = "printing"
            pipeline_state["message"] = f"Sending image {run_index + 1} of {run_count} to print queue..."
            update_job(job_id, status="printing", message=pipeline_state["message"])
            log_event("info", "Processing", pipeline_state["message"], job_id=job_id, filename=filename)
            print_result = await print_output(output_path, load_job(job_id))
            update_job(job_id, **print_result)
            refresh_output_job_metadata(job_id, filename)
            if print_result["print_status"] == "error":
                log_error(
                    f"Print handoff failed for job {job_id} ({filename}): {print_result['print_error']}",
                    "Processing",
                )
            elif print_result["print_status"] == "printed":
                pipeline_state["message"] = f"Image {run_index + 1} of {run_count} sent to print queue"
                log_event("info", "Processing", pipeline_state["message"], job_id=job_id, filename=filename)
            else:
                pipeline_state["message"] = f"Print handoff skipped for run {run_index + 1} of {run_count}"
                log_event("info", "Processing", pipeline_state["message"], job_id=job_id, filename=filename)

        if encourage_variety_across_session and session_interpretation_history:
            log_event(
                "info",
                "Processing",
                "Updating session variety guidance for future jobs...",
                job_id=job_id,
                pipeline_id=pipeline["id"],
            )
            session_variety_text = await compress_meaningful_difference(
                session_interpretation_history,
                pipeline["name"],
                run_count,
                job_id=job_id,
            )
            pipeline_state["session_interpretation_history"] = list(session_interpretation_history)
            pipeline_state["session_variety_text"] = session_variety_text
        elif not encourage_variety_across_session:
            session_variety_text = ""
            pipeline_state["session_interpretation_history"] = []
            pipeline_state["session_variety_text"] = ""

        pipeline_state["variety_guidance_text"] = "\n\n".join(
            part for part in [
                (pipeline_state.get("job_variety_text") or "").strip(),
                (pipeline_state.get("session_variety_text") or "").strip(),
            ]
            if part
        ).strip()
        pipeline_state["meaningful_difference_text"] = pipeline_state["variety_guidance_text"]

        pipeline_state["status"] = "complete"
        pipeline_state["generation_started_at"] = None
        pipeline_state["generation_estimate_seconds"] = None
        if skip_image_generation:
            pipeline_state["message"] = f"Job complete after {run_count} run{'s' if run_count != 1 else ''} with image generation skipped"
        else:
            pipeline_state["message"] = "Job complete"
        pipeline_state["cancel_requested"] = False
        update_job(
            job_id,
            status="complete",
            completed_at=datetime.now().isoformat(),
            message=pipeline_state["message"],
            intermediate_prompt=description or "",
            batch_variety_text=pipeline_state.get("job_variety_text") or "",
            session_variety_text=pipeline_state.get("session_variety_text") or "",
            variety_guidance_text=pipeline_state.get("variety_guidance_text") or "",
            meaningful_difference_text=pipeline_state.get("meaningful_difference_text") or "",
            resolved_interpretation_prompt=resolved_interpretation_prompt,
            resolved_image_prompt=image_prompt,
            generation_started_at=None,
            generation_estimate_seconds=generation_estimate_seconds,
        )
        refresh_all_job_output_metadata(job_id)
        log_event("info", "Processing", pipeline_state["message"], job_id=job_id, pipeline_id=pipeline["id"])
    except asyncio.CancelledError:
        pipeline_state["status"] = "cancelled"
        pipeline_state["message"] = "Cancelled"
        pipeline_state["cancel_requested"] = False
        pipeline_state["generation_started_at"] = None
        pipeline_state["generation_estimate_seconds"] = None
        update_job(
            job_id,
            status="cancelled",
            completed_at=datetime.now().isoformat(),
            message="Cancelled",
            intermediate_prompt=description or "",
            batch_variety_text=pipeline_state.get("job_variety_text") or "",
            session_variety_text=pipeline_state.get("session_variety_text") or "",
            variety_guidance_text=pipeline_state.get("variety_guidance_text") or "",
            meaningful_difference_text=pipeline_state.get("meaningful_difference_text") or "",
            resolved_interpretation_prompt=resolved_interpretation_prompt,
            resolved_image_prompt=image_prompt,
            generation_started_at=None,
            generation_estimate_seconds=generation_estimate_seconds,
        )
        refresh_all_job_output_metadata(job_id)
        log_event("warning", "Processing", f"Job cancelled: {job_id}", job_id=job_id, pipeline_id=pipeline["id"])
        raise
    except Exception as e:
        log_error(str(e), "Processing")
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        pipeline_state["message"] = f"Error: {e}"
        pipeline_state["cancel_requested"] = False
        pipeline_state["generation_started_at"] = None
        pipeline_state["generation_estimate_seconds"] = None
        update_job(
            job_id,
            status="error",
            completed_at=datetime.now().isoformat(),
            error=str(e),
            message=pipeline_state["message"],
            intermediate_prompt=description or "",
            batch_variety_text=pipeline_state.get("job_variety_text") or "",
            session_variety_text=pipeline_state.get("session_variety_text") or "",
            variety_guidance_text=pipeline_state.get("variety_guidance_text") or "",
            meaningful_difference_text=pipeline_state.get("meaningful_difference_text") or "",
            resolved_interpretation_prompt=resolved_interpretation_prompt,
            resolved_image_prompt=image_prompt,
            generation_started_at=None,
            generation_estimate_seconds=generation_estimate_seconds,
        )
        refresh_all_job_output_metadata(job_id)
    finally:
        pipeline_task = None


# --- Serve output images ---

@app.get("/output/{filename}")
async def serve_output(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


# --- Serve frontend ---

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
