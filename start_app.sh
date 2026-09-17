#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "Text2SQL: подготовка приложения..."

if ! command -v docker >/dev/null 2>&1; then
  echo
  echo "Docker Desktop не установлен."
  echo "Установите его с https://www.docker.com/products/docker-desktop/"
  echo "Затем снова откройте START_TEXT2SQL.command."
  read -r -p "Нажмите Enter, чтобы закрыть окно..." _
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Запускаю Docker Desktop..."
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open -a "Docker" || true
  fi
  for _attempt in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo
  echo "Docker Desktop не успел запуститься."
  echo "Дождитесь зелёного статуса Docker и откройте файл ещё раз."
  read -r -p "Нажмите Enter, чтобы закрыть окно..." _
  exit 1
fi

if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c "import streamlit" >/dev/null 2>&1; then
  echo "Первый запуск: устанавливаю компоненты. Это может занять несколько минут."
  ./setup.sh
else
  docker compose up -d
fi

echo "Проверяю базы данных..."
for _attempt in $(seq 1 60); do
  if .venv/bin/python solution/db/check_databases.py >/dev/null 2>&1; then
    break
  fi
  if [ "$_attempt" -eq 60 ]; then
    echo "Базы данных не готовы. Проверьте Docker Desktop и повторите запуск."
    read -r -p "Нажмите Enter, чтобы закрыть окно..." _
    exit 1
  fi
  sleep 2
done

echo
echo "Готово. Сейчас откроется окно Text2SQL в браузере."
echo "Чтобы полностью остановить приложение, вернитесь сюда и нажмите Ctrl+C."
echo

if [[ "$(uname -s)" == "Darwin" ]]; then
  (sleep 3; open "http://localhost:8501") &
fi

exec .venv/bin/python -m streamlit run solution/web_app.py \
  --server.address 127.0.0.1 \
  --server.port 8501 \
  --server.headless false \
  --browser.gatherUsageStats false
