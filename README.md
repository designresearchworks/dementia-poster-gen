# Dementia Design Poster Generator

A research tool that takes co-design workshop images (notes, sketches, ideas), interprets them using Claude to produce a product description aimed at people living with dementia, and then generates a product poster using Nano Banana 2.

The app now supports multiple Markdown-backed pipelines. Each pipeline keeps the same overall structure:

`source images -> interpretation prompt -> descriptive output -> image generation prompt -> generated image`

What changes per pipeline is the interpretation context and the image generation context.

## Pipeline

1. **Drop images** into the `./watch` folder or capture one with the browser webcam
2. **Choose a pipeline** from the browser UI
3. **Edit that pipeline's prompts** in the browser UI if needed
4. **Select which watch-folder images to include**
5. **Click "Interpret Images"**
6. Claude (via OpenRouter) interprets the selected images and produces a draft descriptive output
7. **Review and edit the description** in the browser UI
8. **Click "Generate Poster"**
9. Nano Banana 2 (via Replicate) generates the final output from the reviewed description
10. Output is saved to `./output`, displayed in the browser, and added to the poster library

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

Create a `.env` file (or edit the existing one):

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
REPLICATE_API_TOKEN=r8_your-key-here
```

### 3. Run the server

```bash
uvicorn server:app --reload --port 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Add images

Drop image files (PNG, JPG, JPEG, WEBP) into the `./watch` folder, or use the webcam controls in the browser UI to capture and save a still image there. Click the refresh button in the UI to see them appear. Use the image tiles to select exactly which files should be sent through the pipeline.

## Project structure

```
dementia-poster-gen/
├── server.py              # FastAPI backend
├── static/
│   ├── index.html         # UI
│   ├── style.css          # Styles
│   └── app.js             # Frontend logic
├── watch/                 # Drop input images here
├── output/                # Generated outputs saved here
├── pipelines/             # Markdown pipeline files
│   ├── product-poster.md
│   ├── newspaper-headline.md
│   └── postcard.md
├── .env                   # API keys (do not commit)
├── requirements.txt
└── README.md
```

## Pipelines

Each pipeline is stored as a Markdown file in `./pipelines` and contains:

- A title line starting with `#`
- An `## Interpretation Prompt` section
- An `## Image Generation Prompt` section

The browser UI loads one pipeline at a time. Editing the two prompt textareas updates that pipeline's Markdown file. Use `{description}` in the image generation prompt as the placeholder for the interpreted draft text.

On startup, the app looks for viable Markdown pipelines in `./pipelines`. If it finds at least one valid file, it uses those. If it finds none, it creates a default `product-poster.md` from the built-in hardcoded prompts.

## Notes

- Only the images selected in the browser UI are sent to Claude in a single call
- The selected pipeline controls both the interpretation prompt and the image generation prompt for that run
- The pipeline runs manually (click the button); it does not auto-trigger on new files
- Generated posters are saved with timestamps in `./output`
- Generated posters also appear in the browser poster library; clicking one reloads it into the results panel
- The Replicate API key is sent as a Bearer token; the OpenRouter key likewise
- Rotate your API keys if they've been shared in plain text
