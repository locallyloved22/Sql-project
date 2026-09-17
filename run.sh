#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ]; then
  echo "Сначала выполните ./setup.sh"
  exit 1
fi
exec .venv/bin/python solution/app.py "$@"
