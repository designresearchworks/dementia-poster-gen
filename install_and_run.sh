#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "This script will help you install dependencies, configure API keys, set the watched folder, and run the app."
echo
echo "Before continuing, create and activate your virtual environment if you have not done so already."
echo "Create on macOS/Linux: python3 -m venv venv"
echo "Activate on macOS/Linux: source venv/bin/activate"
echo "Create on Windows (PowerShell): python -m venv venv"
echo "Activate on Windows (PowerShell): .\\venv\\Scripts\\Activate.ps1"
echo
if [[ ! -d "venv" ]]; then
  echo "The ./venv directory does not exist yet."
  echo "Create it first with: python3 -m venv venv"
  exit 1
fi

read -r -p "Have you activated the virtual environment and are you ready to continue? [y/N] " venv_confirm
if [[ ! "$venv_confirm" =~ ^[Yy]$ ]]; then
  echo "Please activate the virtual environment, then run this script again."
  exit 1
fi

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Warning: VIRTUAL_ENV is not set. Continuing because you confirmed manually."
fi

if [[ ! -f "config.json" ]]; then
  cp example.config.json config.json
  echo "Created config.json from example.config.json"
fi

validate_api_keys() {
  python3 - "$1" "$2" <<'PY'
import json
import sys
import httpx

openrouter = (sys.argv[1] or "").strip()
replicate = (sys.argv[2] or "").strip()
result = {
    "openrouter_ok": False,
    "replicate_ok": False,
    "openrouter_message": "missing",
    "replicate_message": "missing",
}

headers = {
    "User-Agent": "dementia-poster-gen-installer/1.0",
}

if openrouter:
    try:
        with httpx.Client(timeout=20.0, headers={**headers, "Authorization": f"Bearer {openrouter}"}) as client:
            response = client.get("https://openrouter.ai/api/v1/models")
        result["openrouter_ok"] = response.status_code == 200
        result["openrouter_message"] = f"status {response.status_code}"
    except Exception as exc:
        result["openrouter_message"] = f"{type(exc).__name__}: {exc}"

if replicate:
    try:
        with httpx.Client(timeout=20.0, headers={**headers, "Authorization": f"Bearer {replicate}"}) as client:
            response = client.get("https://api.replicate.com/v1/account")
        result["replicate_ok"] = response.status_code == 200
        result["replicate_message"] = f"status {response.status_code}"
    except Exception as exc:
        result["replicate_message"] = f"{type(exc).__name__}: {exc}"

print(json.dumps(result))
PY
}

load_env_value() {
  local key="$1"
  python3 - "$key" <<'PY'
import sys
from pathlib import Path

key = sys.argv[1]
env_path = Path(".env")
if not env_path.exists():
    print("")
    raise SystemExit

for line in env_path.read_text().splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    name, value = stripped.split("=", 1)
    if name.strip() == key:
        print(value.strip())
        break
else:
    print("")
PY
}

echo
echo "Installing requirements..."
python3 -m pip install -r requirements.txt

echo
existing_openrouter_key="$(load_env_value "OPENROUTER_API_KEY")"
existing_replicate_token="$(load_env_value "REPLICATE_API_TOKEN")"

if [[ -n "$existing_openrouter_key" || -n "$existing_replicate_token" ]]; then
  echo "Found existing API keys in .env. Testing them..."
  validation_json="$(validate_api_keys "$existing_openrouter_key" "$existing_replicate_token")"
  existing_keys_ok="$(python3 - "$validation_json" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
print("true" if data.get("openrouter_ok") and data.get("replicate_ok") else "false")
PY
)"
  if [[ "$existing_keys_ok" == "true" ]]; then
    echo "Existing API keys are valid. Leaving .env as-is."
  else
    echo "Existing API keys are not valid."
    python3 - "$validation_json" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
print(f"  OpenRouter: {data.get('openrouter_message')}")
print(f"  Replicate: {data.get('replicate_message')}")
PY
    existing_openrouter_key=""
    existing_replicate_token=""
  fi
fi

while [[ -z "$existing_openrouter_key" || -z "$existing_replicate_token" ]]; do
  read -r -p "OpenRouter API key: " openrouter_key
  read -r -p "Replicate API token: " replicate_token
  validation_json="$(validate_api_keys "$openrouter_key" "$replicate_token")"
  keys_ok="$(python3 - "$validation_json" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
print("true" if data.get("openrouter_ok") and data.get("replicate_ok") else "false")
PY
)"
  if [[ "$keys_ok" == "true" ]]; then
    cat > .env <<EOF
OPENROUTER_API_KEY=${openrouter_key}
REPLICATE_API_TOKEN=${replicate_token}
EOF
    echo "Wrote .env"
    existing_openrouter_key="$openrouter_key"
    existing_replicate_token="$replicate_token"
  else
    echo "Error with API keys, please provide new ones"
    python3 - "$validation_json" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
print(f"  OpenRouter: {data.get('openrouter_message')}")
print(f"  Replicate: {data.get('replicate_message')}")
PY
  fi
done

current_watch_folder="$(python3 - <<'PY'
import json
from pathlib import Path
config = json.loads(Path('config.json').read_text())
print(config.get('watched_folder') or '')
PY
)"

echo
echo "Set the watched folder path. This is the folder the app will monitor for new images."
read -r -p "Watched folder [${current_watch_folder}]: " watched_folder_input
watched_folder="${watched_folder_input:-$current_watch_folder}"

python3 - "$watched_folder" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path("config.json")
config = json.loads(config_path.read_text())
config["watched_folder"] = sys.argv[1]
config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
PY
echo "Updated config.json watched_folder"

echo
echo "Checking config and required folders..."
python3 check_config.py --fix

echo
echo "Launching app on http://127.0.0.1:8000"
exec uvicorn server:app --reload --port 8000
