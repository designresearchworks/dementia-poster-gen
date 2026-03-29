"""
Dementia Design Poster Generator
FastAPI backend: watches a folder for images, interprets them via Claude (OpenRouter),
generates product posters via Nano Banana 2 (Replicate).
"""

import asyncio
import base64
import json
import os
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
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from starlette.background import BackgroundTask

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

WATCH_DIR = Path(__file__).parent / "watch"
OUTPUT_DIR = Path(__file__).parent / "output"
PIPELINES_DIR = Path(__file__).parent / "pipelines"
PROMPT_LOGS_DIR = Path(__file__).parent / "Prompt Logs"
CONFIG_FILE = Path(__file__).parent / "config.json"

WATCH_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PIPELINES_DIR.mkdir(exist_ok=True)
PROMPT_LOGS_DIR.mkdir(exist_ok=True)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
EXTRACTED_CONCEPTS_TOKEN = "{extracted-concepts}"
MEANINGFUL_DIFFERENCE_TOKEN = "{meaningfuldifference}"
EXTRACTED_CONCEPTS_PROMPT = (
    "Look at these source images and extract the key concepts, themes, activities, emotions, and needs they contain. "
    "Return only a concise comma-separated list of extracted concepts. No markdown, no bullets, no explanation."
)
MEANINGFUL_DIFFERENCE_COMPRESSION_PROMPT = (
    "You will be given earlier interpretations from a design ideation run. Create a list of product names, "
    "technologies, features, and contexts that have been included in these earlier interpretations. Capture the "
    "shape of the idea. Do not create any markdown or headers. Just output a simple list of features and technologies. "
    "The list need not be exhaustive, but should include from 10-30 items that capture the spirit of the previous "
    "interpretations best.\n\n"
    "<previousinterpretations>\n{previous_interpretations}\n</previousinterpretations>"
)
TEXT_MODELS = {
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
    "openrouter:google/gemini-3.1-flash-image-preview": {
        "label": "Gemini 3.1 Flash Image Preview (OpenRouter)",
        "provider": "openrouter",
        "model": "google/gemini-3.1-flash-image-preview",
    },
}
ASPECT_RATIOS = {"1:1", "3:2", "2:3", "3:4", "4:3", "9:16", "16:9"}

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
        "path": str(pipeline_path(pipeline_id)),
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


def ensure_config() -> dict:
    existing = load_config()
    fallback_pipeline_id = get_fallback_pipeline_id()
    existing_layout = existing.get("layout") or {}
    normalized = {
        "default_pipeline_id": existing.get("default_pipeline_id")
        if existing.get("default_pipeline_id") in list_viable_pipeline_ids()
        else fallback_pipeline_id,
        "debug_mode": bool(existing.get("debug_mode", False)),
        "skip_image_generation": bool(existing.get("skip_image_generation", False)),
        "text_model": existing.get("text_model")
        if existing.get("text_model") in TEXT_MODELS
        else "anthropic/claude-opus-4.6",
        "image_model": existing.get("image_model")
        if existing.get("image_model") in IMAGE_MODELS
        else "replicate:google/nano-banana-pro",
        "restore_settings": {
            "interpretation_prompt": bool((existing.get("restore_settings") or {}).get("interpretation_prompt", True)),
            "description": bool((existing.get("restore_settings") or {}).get("description", True)),
            "image_generation_prompt": bool((existing.get("restore_settings") or {}).get("image_generation_prompt", True)),
            "image_model": bool((existing.get("restore_settings") or {}).get("image_model", True)),
            "aspect_ratio": bool((existing.get("restore_settings") or {}).get("aspect_ratio", True)),
        },
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


runtime_errors: list[dict] = []


def log_error(message: str, source: str = "server"):
    runtime_errors.append({
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "message": message,
    })
    del runtime_errors[:-100]


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


def get_text_model() -> str:
    return str(ensure_config().get("text_model", "anthropic/claude-opus-4.6"))


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


def get_restore_settings() -> dict:
    return dict(ensure_config().get("restore_settings", {}))


def get_layout_settings() -> dict:
    return dict(ensure_config().get("layout", {}))


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
    path = pipeline_path(pipeline_id)
    if not path.exists():
        raise HTTPException(404, f"Pipeline not found: {pipeline_id}")
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

pipeline_state = {
    "status": "idle",  # idle | interpreting | generating | downloading | cancelling | complete | cancelled | error
    "message": "",
    "description": None,
    "poster_filename": None,
    "poster_filenames": [],
    "error": None,
    "started_at": None,
    "source_images": [],
    "pipeline_id": current_pipeline_id,
    "image_model": get_default_image_model(),
    "aspect_ratio": "3:4",
    "run_count": 1,
    "completed_runs": 0,
    "current_run": 0,
    "rerun_interpretation": False,
    "cycle_pipelines": False,
    "encourage_variety": False,
    "interpretation_history": [],
    "meaningful_difference_text": "",
    "extracted_concepts": "",
    "cancel_requested": False,
}


# --- FastAPI app ---

app = FastAPI(title="Dementia Design Poster Generator")


# --- Helper functions ---

def get_image_files() -> list[Path]:
    """Return all image files in the watch directory, newest first."""
    files = []
    for f in WATCH_DIR.iterdir():
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


def resolve_watch_image(filename: str) -> Path:
    """Resolve a single safe watch-folder image path."""
    if not filename:
        raise HTTPException(400, "No filename provided")

    for path in get_image_files():
        if path.name == filename:
            return path

    raise HTTPException(404, f"Image not found in watch folder: {filename}")


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
    output_path = WATCH_DIR / filename

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
    output_path = WATCH_DIR / filename
    with open(output_path, "wb") as f:
        f.write(contents)
    return filename


def build_library_index() -> list[dict]:
    """Return poster-library entries derived directly from output files."""
    entries = []
    for path in sorted(OUTPUT_DIR.iterdir(), key=lambda file_path: file_path.stat().st_mtime, reverse=True):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        metadata = read_output_metadata(path)
        created_at = metadata.get("created_at") or datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        source_images = parse_source_images(metadata.get("source_images"))

        entries.append({
            "poster_filename": path.name,
            "description": metadata.get("description"),
            "extracted_concepts": metadata.get("extracted_concepts"),
            "created_at": created_at,
            "source_images": source_images,
            "pipeline_id": metadata.get("pipeline_id"),
            "pipeline_name": metadata.get("pipeline_name"),
            "interpretation_prompt": metadata.get("interpretation_prompt"),
            "image_generation_prompt": metadata.get("image_generation_prompt"),
            "resolved_image_generation_prompt": metadata.get("resolved_image_generation_prompt"),
            "image_model": metadata.get("image_model"),
            "aspect_ratio": metadata.get("aspect_ratio"),
        })

    return entries


def safe_output_member_path(name: str) -> Path:
    target = (OUTPUT_DIR / Path(name).name).resolve()
    if target.parent != OUTPUT_DIR.resolve():
        raise HTTPException(400, "Invalid archive entry")
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
        log_error(f"Could not read metadata from {path.name}: {exc}", "metadata")
        return {}

    metadata = {}
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
            metadata[key] = value
    return metadata
async def call_claude(
    images: list[Path],
    prompt: str,
    pipeline_name: str = "",
    run_number: Optional[int] = None,
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
        log_error(
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
            "interpretation-trace",
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
                "interpretation",
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
        MEANINGFUL_DIFFERENCE_COMPRESSION_PROMPT.format(previous_interpretations=raw_history),
        pipeline_name=f"{pipeline_name} Meaningful Difference Compression",
        run_number=run_number,
        prompt_kind="meaningfuldifference-compression",
    )
    normalized = (compressed or "").strip()
    if normalized:
        return normalized

    log_error(
        f"Meaningful-difference compression was blank for run {run_number} using {pipeline_name}. Falling back to raw history.",
        "meaningfuldifference-compression",
    )
    return raw_history


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


async def save_generated_image(image_result: str, provider: str, filename: str, metadata: Optional[dict[str, str]] = None) -> Path:
    if provider == "replicate":
        return await download_image(image_result, filename, metadata)
    if provider == "openrouter":
        return save_data_url_image(image_result, filename, metadata)
    raise Exception(f"Unsupported image provider: {provider}")


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
    path = pipeline_path(pipeline_id)
    if not path.exists():
        raise HTTPException(404, f"Pipeline not found: {pipeline_id}")

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

    path = pipeline_path(pipeline_id)
    if not path.exists():
        raise HTTPException(404, f"Pipeline not found: {pipeline_id}")

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
    return {
        "default_pipeline_id": get_default_pipeline_id(),
        "available_pipeline_ids": list_viable_pipeline_ids(),
        "debug_mode": get_debug_mode(),
        "skip_image_generation": get_skip_image_generation(),
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
        "restore_settings": get_restore_settings(),
        "layout": get_layout_settings(),
    }


@app.put("/api/settings")
async def update_settings(body: dict):
    pipeline_id = (body or {}).get("default_pipeline_id")
    viable_ids = list_viable_pipeline_ids()
    if pipeline_id not in viable_ids:
        raise HTTPException(400, "Invalid default pipeline")

    requested_layout = (body or {}).get("layout") or {}
    content_row_height = requested_layout.get("content_row_height", get_layout_settings().get("content_row_height", 448))
    if not isinstance(content_row_height, (int, float)):
        content_row_height = get_layout_settings().get("content_row_height", 448)
    content_row_height = max(220, min(1200, int(content_row_height)))

    save_config({
        "default_pipeline_id": pipeline_id,
        "debug_mode": bool((body or {}).get("debug_mode", False)),
        "skip_image_generation": bool((body or {}).get("skip_image_generation", False)),
        "text_model": (body or {}).get("text_model")
        if (body or {}).get("text_model") in TEXT_MODELS
        else get_text_model(),
        "image_model": (body or {}).get("image_model")
        if (body or {}).get("image_model") in IMAGE_MODELS
        else get_default_image_model(),
        "restore_settings": {
            "interpretation_prompt": bool(((body or {}).get("restore_settings") or {}).get("interpretation_prompt", True)),
            "description": bool(((body or {}).get("restore_settings") or {}).get("description", True)),
            "image_generation_prompt": bool(((body or {}).get("restore_settings") or {}).get("image_generation_prompt", True)),
            "image_model": bool(((body or {}).get("restore_settings") or {}).get("image_model", True)),
            "aspect_ratio": bool(((body or {}).get("restore_settings") or {}).get("aspect_ratio", True)),
        },
        "layout": {
            "content_row_height": content_row_height,
        },
    })
    pipeline_state["image_model"] = get_default_image_model()

    return {
        "ok": True,
        "default_pipeline_id": get_default_pipeline_id(),
        "debug_mode": get_debug_mode(),
        "skip_image_generation": get_skip_image_generation(),
        "text_model": get_text_model(),
        "image_model": get_default_image_model(),
        "restore_settings": get_restore_settings(),
        "layout": get_layout_settings(),
    }


@app.get("/api/errors")
async def get_errors():
    return {"items": runtime_errors}


@app.post("/api/errors")
async def add_error(body: dict):
    message = (body or {}).get("message", "").strip()
    source = (body or {}).get("source", "client").strip() or "client"
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


@app.get("/api/status")
async def get_status():
    return pipeline_state


@app.post("/api/cancel")
async def cancel_pipeline():
    global pipeline_task
    if pipeline_state["status"] not in ("interpreting", "generating", "downloading") or pipeline_task is None:
        raise HTTPException(400, "No active pipeline to cancel")

    pipeline_state["cancel_requested"] = True
    pipeline_state["status"] = "cancelling"
    pipeline_state["message"] = "Cancelling current batch..."
    pipeline_task.cancel()
    return {"ok": True, "status": "cancelling"}


@app.post("/api/meaningful-difference/clear")
async def clear_meaningful_difference():
    if pipeline_state["status"] in ("interpreting", "generating", "downloading", "cancelling"):
        raise HTTPException(400, "Cannot clear meaningful difference while pipeline is running")

    pipeline_state["interpretation_history"] = []
    pipeline_state["meaningful_difference_text"] = ""
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
        for path in sorted(OUTPUT_DIR.iterdir()):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            archive.write(path, arcname=path.name)

    filename = f"library_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@app.post("/api/library/import")
async def import_library(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Upload a zip file")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Uploaded zip is empty")

    try:
        with ZipFile(BytesIO(contents)) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            imported = 0
            for member in members:
                member_name = Path(member.filename).name
                if not member_name:
                    continue
                if Path(member_name).suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                target = safe_output_member_path(member_name)
                with archive.open(member) as source, open(target, "wb") as destination:
                    destination.write(source.read())
                imported += 1
    except BadZipFile as exc:
        raise HTTPException(400, "Invalid zip file") from exc

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
    aspect_ratio = (body.get("aspect_ratio") or "3:4").strip() if body else "3:4"
    run_count = int((body.get("run_count") or 1)) if body else 1
    cycle_pipelines = bool((body.get("cycle_pipelines") or False)) if body else False
    encourage_variety = bool((body.get("encourage_variety") or False)) if body else False
    if not isinstance(selected_filenames, list) or not selected_filenames:
        raise HTTPException(400, "No images selected")
    if not pipeline_id:
        raise HTTPException(400, "No pipeline selected")
    image_model_option = get_image_model_option(image_model)
    if aspect_ratio not in ASPECT_RATIOS:
        raise HTTPException(400, "Invalid aspect ratio")
    if run_count < 1 or run_count > 20:
        raise HTTPException(400, "Run count must be between 1 and 20")

    effective_cycle_pipelines = cycle_pipelines if run_count > 1 else False
    effective_rerun_interpretation = run_count > 1
    effective_encourage_variety = encourage_variety

    images = resolve_selected_images(selected_filenames)
    pipeline = load_pipeline(pipeline_id)
    if interpretation_prompt:
        pipeline["interpretation"] = interpretation_prompt
    if image_generation_prompt:
        pipeline["image"] = image_generation_prompt

    existing_interpretation_history = list(pipeline_state.get("interpretation_history") or [])
    existing_meaningful_difference_text = pipeline_state.get("meaningful_difference_text") or ""

    # Reset state
    pipeline_state.update({
        "status": "interpreting",
        "message": f"Sending {len(images)} image(s) to Claude for interpretation...",
        "description": None,
        "poster_filename": None,
        "poster_filenames": [],
        "error": None,
        "started_at": datetime.now().isoformat(),
        "source_images": selected_filenames,
        "pipeline_id": pipeline["id"],
        "image_model": image_model,
        "aspect_ratio": aspect_ratio,
        "run_count": run_count,
        "completed_runs": 0,
        "current_run": 0,
        "rerun_interpretation": effective_rerun_interpretation,
        "cycle_pipelines": effective_cycle_pipelines,
        "encourage_variety": effective_encourage_variety,
        "interpretation_history": existing_interpretation_history,
        "meaningful_difference_text": existing_meaningful_difference_text,
        "extracted_concepts": "",
        "cancel_requested": False,
    })

    pipeline_task = asyncio.create_task(
        _run_pipeline(
            images,
            pipeline,
            image_model_option,
            aspect_ratio,
            run_count,
            effective_rerun_interpretation,
            effective_cycle_pipelines,
            effective_encourage_variety,
        )
    )

    return {"ok": True, "status": "interpreting", "image_count": len(images), "run_count": run_count}

async def _run_pipeline(
    images: list[Path],
    pipeline: dict,
    image_model_option: dict,
    aspect_ratio: str,
    run_count: int,
    rerun_interpretation: bool,
    cycle_pipelines: bool,
    encourage_variety: bool,
):
    """Run interpretation and generation end-to-end."""
    global pipeline_task
    try:
        description = None
        interpretation_history: list[str] = list(pipeline_state.get("interpretation_history") or [])
        meaningful_difference_text = pipeline_state.get("meaningful_difference_text") or ""
        extracted_concepts = ""
        skip_image_generation = get_skip_image_generation()
        pipeline_ids = list_viable_pipeline_ids()
        current_index = pipeline_ids.index(pipeline["id"]) if pipeline["id"] in pipeline_ids else 0

        pipeline_state["status"] = "interpreting"
        pipeline_state["message"] = f"Extracting concepts from {len(images)} source image(s)..."
        extracted_concepts = await call_claude(
            images,
            EXTRACTED_CONCEPTS_PROMPT,
            pipeline_name="Extracted Concepts",
            run_number=0,
            prompt_kind="extracted-concepts",
        )
        extracted_concepts = require_extracted_concepts(extracted_concepts)
        pipeline_state["extracted_concepts"] = extracted_concepts

        for run_index in range(run_count):
            active_pipeline = pipeline
            if cycle_pipelines and pipeline_ids:
                active_pipeline_id = pipeline_ids[(current_index + run_index) % len(pipeline_ids)]
                active_pipeline = load_pipeline(active_pipeline_id)
            pipeline_state["pipeline_id"] = active_pipeline["id"]
            pipeline_state["current_run"] = run_index + 1
            if run_index == 0 or rerun_interpretation:
                pipeline_state["status"] = "interpreting"
                resolved_interpretation_prompt = active_pipeline["interpretation"].replace(
                    EXTRACTED_CONCEPTS_TOKEN,
                    extracted_concepts,
                )
                meaningful_difference_text = ""
                meaningful_difference_sources: list[str] = []
                should_inject_meaningful_difference = (
                    encourage_variety
                    and MEANINGFUL_DIFFERENCE_TOKEN in active_pipeline["interpretation"]
                )
                if should_inject_meaningful_difference and interpretation_history:
                    meaningful_difference_sources.extend(interpretation_history)
                if should_inject_meaningful_difference and meaningful_difference_sources:
                    pipeline_state["message"] = (
                        f"Compressing previous interpretations for run {run_index + 1} of {run_count}..."
                    )
                    meaningful_difference_text = await compress_meaningful_difference(
                        meaningful_difference_sources,
                        active_pipeline["name"],
                        run_index + 1,
                    )
                resolved_interpretation_prompt = resolved_interpretation_prompt.replace(
                    MEANINGFUL_DIFFERENCE_TOKEN,
                    meaningful_difference_text,
                )
                pipeline_state["meaningful_difference_text"] = meaningful_difference_text
                if run_count > 1 and rerun_interpretation:
                    pipeline_state["message"] = (
                        f"Creating intermediate prompt for run {run_index + 1} of {run_count} with {active_pipeline['name']}..."
                    )
                else:
                    pipeline_state["message"] = f"Creating intermediate prompt for run {run_index + 1} with {active_pipeline['name']}..."
                description = await call_claude(
                    [],
                    resolved_interpretation_prompt,
                    pipeline_name=active_pipeline["name"],
                    run_number=run_index + 1,
                    encourage_variety=encourage_variety,
                    previous_interpretations=interpretation_history,
                    meaningful_difference_text=meaningful_difference_text,
                    prompt_kind="intermediate-prompt",
                )
                description = require_description(description, active_pipeline["name"], run_index + 1)
                pipeline_state["description"] = description
                interpretation_history.append(description)
                pipeline_state["interpretation_history"] = list(interpretation_history)

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
                        "run_number": run_index + 1,
                        "run_count": run_count,
                        "image_model": pipeline_state["image_model"],
                        "aspect_ratio": aspect_ratio,
                    },
                )
                if should_inject_meaningful_difference:
                    pipeline_state["message"] = (
                        f"Updating meaningful difference after run {run_index + 1} of {run_count}..."
                    )
                    meaningful_difference_text = await compress_meaningful_difference(
                        interpretation_history,
                        active_pipeline["name"],
                        run_index + 1,
                    )
                    pipeline_state["meaningful_difference_text"] = meaningful_difference_text
                continue
            pipeline_state["status"] = "generating"
            pipeline_state["message"] = (
                f"Generating image {run_index + 1} of {run_count} with {active_pipeline['name']} via {image_model_option['label']}..."
            )
            if image_model_option["provider"] == "replicate":
                image_result = await call_replicate(
                    image_prompt,
                    image_model_option["model"],
                    aspect_ratio,
                    prompt_metadata={
                        "pipeline_id": active_pipeline["id"],
                        "pipeline_name": active_pipeline["name"],
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
                        "run_number": run_index + 1,
                        "run_count": run_count,
                        "image_model": pipeline_state["image_model"],
                    },
                )

            pipeline_state["status"] = "downloading"
            pipeline_state["message"] = f"Saving image {run_index + 1} of {run_count}..."

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"poster_{timestamp}.png"
            await save_generated_image(
                image_result,
                image_model_option["provider"],
                filename,
                metadata={
                    "pipeline_id": active_pipeline["id"],
                    "pipeline_name": active_pipeline["name"],
                    "interpretation_prompt": active_pipeline["interpretation"],
                    "description": description,
                    "extracted_concepts": extracted_concepts,
                    "image_generation_prompt": active_pipeline["image"],
                    "resolved_image_generation_prompt": image_prompt,
                    "image_model": pipeline_state["image_model"],
                    "image_provider": image_model_option["provider"],
                    "aspect_ratio": aspect_ratio,
                    "source_images": json.dumps([path.name for path in images]),
                    "created_at": datetime.now().isoformat(),
                },
            )

            pipeline_state["poster_filename"] = filename
            pipeline_state["poster_filenames"].append(filename)
            pipeline_state["completed_runs"] = run_index + 1
            if should_inject_meaningful_difference:
                pipeline_state["message"] = (
                    f"Updating meaningful difference after run {run_index + 1} of {run_count}..."
                )
                meaningful_difference_text = await compress_meaningful_difference(
                    interpretation_history,
                    active_pipeline["name"],
                    run_index + 1,
                )
                pipeline_state["meaningful_difference_text"] = meaningful_difference_text

        pipeline_state["status"] = "complete"
        if skip_image_generation:
            pipeline_state["message"] = f"Finished {run_count} run{'s' if run_count != 1 else ''} with image generation skipped"
        else:
            pipeline_state["message"] = f"Finished {run_count} run{'s' if run_count != 1 else ''}"
        pipeline_state["cancel_requested"] = False
    except asyncio.CancelledError:
        pipeline_state["status"] = "cancelled"
        pipeline_state["message"] = "Cancelled"
        pipeline_state["cancel_requested"] = False
        raise
    except Exception as e:
        log_error(str(e), "pipeline")
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        pipeline_state["message"] = f"Error: {e}"
        pipeline_state["cancel_requested"] = False
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
