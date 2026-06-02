# Dementia Poster Generator

File-driven poster generation for dementia design/co-design workflows.

The app watches a folder for new source images, interprets them with a text model, generates poster images with an image model, saves the outputs with embedded job metadata, and can optionally hand completed outputs to a printer.

## What It Does

- Watches a configured folder for new source images
- Creates one job per new file
- Extracts concepts from the source image(s)
- Builds an interpretation prompt from the selected pipeline
- Generates an intermediate prompt with the selected LLM
- Generates an output image with the selected image model
- Saves the result into `output/`
- Stores job records in `jobs/`
- Optionally sends the finished output to the configured printer

The browser UI is mainly for:

- setup/configuration
- monitoring the system log
- inspecting active and previous jobs
- viewing saved outputs in the library
- manual runs and testing

## Main Folders

- `watch/`
  Source images the watcher monitors by default
- `output/`
  Generated poster images
- `jobs/`
  File-backed JSON job records
- `pipelines/`
  Markdown pipeline definitions
- `Prompt Logs/`
  Saved prompt logs for text/image calls

## Requirements

- Python 3
- A virtual environment
- OpenRouter API key
- Replicate API token

## Quick Start

The easiest path is the bootstrap script:

```bash
./install_and_run.sh
```

That script will:

1. Tell you how to create and activate a virtual environment
2. Check that `venv/` exists
3. Install `requirements.txt`
4. Reuse `.env` if valid keys are already present
5. Ask for new API keys if the existing ones are missing or invalid
6. Ask for the watched folder
7. Run the config checker and create missing folders
8. Launch:

```bash
uvicorn server:app --reload --port 8000
```

Then open:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## Manual Setup

Create and activate a virtual environment:

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create `.env` from the example:

```bash
cp example.env .env
```

Create `config.json` from the example if needed:

```bash
cp example.config.json config.json
```

Check config and required folders:

```bash
python3 check_config.py --fix
```

Run the app:

```bash
uvicorn server:app --reload --port 8000
```

## Environment Variables

See:

- example.env
- .env.example

Required keys:

- `OPENROUTER_API_KEY`
- `REPLICATE_API_TOKEN`

## Config

See:

- example.config.json

Important settings include:

- `watched_folder`
- `default_pipeline_id`
- `text_model`
- `image_model`
- `aspect_ratio`
- `run_count`
- `watcher_enabled`
- `send_to_printer`
- `printer_name`

Default watched folder:

```json
"watched_folder": "watch/"
```

That works out of the box relative to the project root, but it can be changed in the UI.

## Pipelines

Pipelines live in `pipelines/` as Markdown files.

Each pipeline contains:

- `# Title`
- `## Interpretation Prompt`
- `## Image Generation Prompt`

The interpretation prompt can use:

- `{extracted-concepts}`

The image prompt can use:

- `{description}`

Pipelines are now resolved by their real filename stem, so names with spaces are supported.

## Variety System

There are two separate variety options:

- `Encourage variety within batches`
  Varies repeated runs inside one job
- `Encourage variety across session`
  Carries variety memory across jobs during the current server session

Variety guidance is appended at runtime to the interpretation prompt and is also shown in the UI.

## Printing

Printing is optional.

If `Send to printer` is enabled and a printer is selected, completed jobs hand the saved output image to the local print system. The app treats printing as a handoff, not as confirmation of physical print completion.

## Skip Image Generation

If `Skip image generation` is enabled:

- the image model call is skipped
- a placeholder PNG is created in `output/`
- that placeholder is still treated like a normal output for library/job inspection

## Job Browser

The job browser shows:

- the active job
- queued jobs
- previous jobs

You can:

- inspect job JSON
- preview input/output images
- requeue source images
- feed an output back into the watch folder
- reprint previous outputs
- remove queued items
- restart the queue worker

## System Log

The system log is the main operational feed.

It shows structured events from:

- watch folder activity
- jobs/queue
- processing stages
- system events
- browser-reported errors

High-frequency HTTP access logs are suppressed by default unless explicitly enabled in settings.

## Library

The library is built dynamically from files in `output/`.

Each PNG stores embedded `job_json` metadata, which is used for:

- library display
- metadata reload
- debugging
- restore/import behavior

## Backup / Restore

In Settings, `Data Backup/Restore` can export and import a zip containing:

- `jobs/`
- `watch/`
- `output/`

Import behavior:

- asks for confirmation
- clears current contents of those folders
- pauses watcher/queue processing
- restores the archive
- restarts the queue worker
- resets the watcher baseline to the restored watch-folder contents

Run the app manually:

```bash
uvicorn server:app --reload --port 8000
```


