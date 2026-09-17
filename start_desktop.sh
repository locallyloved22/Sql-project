#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "Text2SQL: готовлю desktop-приложение..."
./prepare_for_vscode.sh

if ! .venv/bin/python -c "import tkinter" >/dev/null 2>&1; then
  echo "В этом Python отсутствует Tkinter. Используйте ./start_app.sh"
  exit 1
fi

echo "Открываю окно Text2SQL..."
exec .venv/bin/python solution/desktop_app.py
