#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not available in PATH." >&2
  exit 1
fi

echo "Starting Enterprise Knowledge Platform Demo..."
docker compose -f compose.demo.yml up --build

