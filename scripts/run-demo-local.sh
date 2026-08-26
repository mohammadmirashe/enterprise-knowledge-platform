#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

export DEMO_MODE=true
export SQLITE_PATH=.demo/storage/knowledge.db
export UPLOADS_DIR=.demo/data/uploads
export PROCESSED_DIR=.demo/data/processed
export VECTOR_DIR=.demo/storage/vector_db
export API_URL=http://127.0.0.1:8000
export PUBLIC_API_URL="$API_URL"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

mkdir -p .demo/storage

"$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

attempt=0
until "$PYTHON_BIN" -c "import urllib.request; urllib.request.urlopen('$API_URL/health', timeout=2)" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Demo API did not become ready." >&2
    exit 1
  fi
  sleep 1
done

echo "Demo is ready at http://localhost:8501"
"$PYTHON_BIN" -m streamlit run ui.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true

