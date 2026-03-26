"""
Dementia Design Poster Generator
FastAPI backend: watches a folder for images, interprets them via Claude (OpenRouter),
generates product posters via Nano Banana 2 (Replicate).
"""

import asyncio
import base64
import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from PIL.PngImagePlugin import PngInfo

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

WATCH_DIR = Path(__file__).parent / "watch"
OUTPUT_DIR = Path(__file__).parent / "output"
PIPELINES_DIR = Path(__file__).parent / "pipelines"
CONFIG_FILE = Path(__file__).parent / "config.json"

WATCH_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PIPELINES_DIR.mkdir(exist_ok=True)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

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


runtime_errors: list[dict] = []


def log_error(message: str, source: str = "server"):
    runtime_errors.append({
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "message": message,
    })
    del runtime_errors[:-100]


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


def get_default_pipeline_id() -> str:
    viable_ids = list_viable_pipeline_ids()
    if not viable_ids:
        return ensure_default_pipeline()

    config = load_config()
    configured = config.get("default_pipeline_id")
    if configured in viable_ids:
        return configured

    fallback = "product-poster" if "product-poster" in viable_ids else viable_ids[0]
    if configured != fallback:
        save_config({"default_pipeline_id": fallback})
    return fallback


def get_debug_mode() -> bool:
    return bool(load_config().get("debug_mode", False))


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
current_pipeline_id = get_default_pipeline_id()
current_pipeline = load_pipeline(current_pipeline_id)

pipeline_state = {
    "status": "idle",  # idle | interpreting | generating | downloading | complete | error
    "message": "",
    "description": None,
    "poster_filename": None,
    "error": None,
    "started_at": None,
    "source_images": [],
    "pipeline_id": current_pipeline_id,
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
            "created_at": created_at,
            "source_images": source_images,
            "pipeline_id": metadata.get("pipeline_id"),
            "pipeline_name": metadata.get("pipeline_name"),
            "interpretation_prompt": metadata.get("interpretation_prompt"),
            "image_generation_prompt": metadata.get("image_generation_prompt"),
            "resolved_image_generation_prompt": metadata.get("resolved_image_generation_prompt"),
        })

    return entries


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
        "image_generation_prompt",
        "resolved_image_generation_prompt",
        "source_images",
        "created_at",
    ):
        value = info.get(key)
        if isinstance(value, str) and value:
            metadata[key] = value
    return metadata
async def call_claude(images: list[Path], prompt: str) -> str:
    """Send images + prompt to Claude via OpenRouter and return the text response."""
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
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": "anthropic/claude-opus-4.6",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": content}
        ],
    }

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
        return data["choices"][0]["message"]["content"]


async def call_replicate(prompt: str) -> str:
    """Send prompt to Nano Banana 2 via Replicate and return the output image URL."""
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "3:4",
        }
    }

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        # Try sync mode first (waits up to 60s)
        resp = await client.post(
            "https://api.replicate.com/v1/models/google/nano-banana-2/predictions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
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
    }


@app.put("/api/settings")
async def update_settings(body: dict):
    global current_pipeline_id, current_pipeline
    pipeline_id = (body or {}).get("default_pipeline_id")
    viable_ids = list_viable_pipeline_ids()
    if pipeline_id not in viable_ids:
        raise HTTPException(400, "Invalid default pipeline")

    save_config({
        "default_pipeline_id": pipeline_id,
        "debug_mode": bool((body or {}).get("debug_mode", False)),
    })
    current_pipeline_id = pipeline_id
    current_pipeline = load_pipeline(current_pipeline_id)
    pipeline_state["pipeline_id"] = current_pipeline_id

    return {
        "ok": True,
        "default_pipeline_id": current_pipeline_id,
        "debug_mode": get_debug_mode(),
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


@app.delete("/api/images/{filename}")
async def delete_image(filename: str):
    path = resolve_watch_image(filename)
    path.unlink()
    return {"ok": True, "filename": filename}


@app.get("/api/status")
async def get_status():
    return pipeline_state


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


@app.post("/api/run")
async def run_pipeline(body: dict):
    """Trigger the full pipeline."""
    if pipeline_state["status"] not in ("idle", "complete", "error"):
        raise HTTPException(400, "Pipeline is already running")

    selected_filenames = body.get("filenames") if body else None
    pipeline_id = body.get("pipeline_id") if body else None
    interpretation_prompt = (body.get("interpretation_prompt") or "").strip() if body else ""
    image_generation_prompt = (body.get("image_generation_prompt") or "").strip() if body else ""
    if not isinstance(selected_filenames, list) or not selected_filenames:
        raise HTTPException(400, "No images selected")
    if not pipeline_id:
        raise HTTPException(400, "No pipeline selected")

    images = resolve_selected_images(selected_filenames)
    pipeline = load_pipeline(pipeline_id)
    if interpretation_prompt:
        pipeline["interpretation"] = interpretation_prompt
    if image_generation_prompt:
        pipeline["image"] = image_generation_prompt

    # Reset state
    pipeline_state.update({
        "status": "interpreting",
        "message": f"Sending {len(images)} image(s) to Claude for interpretation...",
        "description": None,
        "poster_filename": None,
        "error": None,
        "started_at": datetime.now().isoformat(),
        "source_images": selected_filenames,
        "pipeline_id": pipeline["id"],
    })

    asyncio.create_task(_run_pipeline(images, pipeline))

    return {"ok": True, "status": "interpreting", "image_count": len(images)}

async def _run_pipeline(images: list[Path], pipeline: dict):
    """Run interpretation and generation end-to-end."""
    try:
        pipeline_state["status"] = "interpreting"
        pipeline_state["message"] = f"Claude is interpreting {len(images)} image(s)..."

        description = await call_claude(images, pipeline["interpretation"])
        pipeline_state["description"] = description
        pipeline_state["status"] = "generating"
        pipeline_state["message"] = "Description ready. Generating output..."
        image_prompt = pipeline["image"].replace("{description}", description)
        image_url = await call_replicate(image_prompt)

        pipeline_state["status"] = "downloading"
        pipeline_state["message"] = "Downloading generated poster..."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"poster_{timestamp}.png"
        await download_image(
            image_url,
            filename,
            metadata={
                "pipeline_id": pipeline["id"],
                "pipeline_name": pipeline["name"],
                "interpretation_prompt": pipeline["interpretation"],
                "description": description,
                "image_generation_prompt": pipeline["image"],
                "resolved_image_generation_prompt": image_prompt,
                "source_images": json.dumps([path.name for path in images]),
                "created_at": datetime.now().isoformat(),
            },
        )

        pipeline_state["poster_filename"] = filename
        pipeline_state["status"] = "complete"
        pipeline_state["message"] = "Poster generated!"
    except Exception as e:
        log_error(str(e), "pipeline")
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        pipeline_state["message"] = f"Error: {e}"


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
