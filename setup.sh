#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker не установлен."
  echo "Установите Docker Desktop: https://www.docker.com/products/docker-desktop/"
  echo "Запустите Docker Desktop и повторите: ./setup.sh"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker установлен, но Docker Engine не запущен. Откройте Docker Desktop и повторите ./setup.sh"
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r solution/requirements.txt

if [ ! -f solution/.env ]; then
  cp solution/.env.example solution/.env
  echo "Создан solution/.env. Перед настоящей LLM заполните LLM_API_KEY и LLM_MODEL."
fi

.venv/bin/python solution/db/build_data.py
docker compose up -d

echo "Ожидаю готовности пяти PostgreSQL-контейнеров..."
for attempt in $(seq 1 60); do
  initialized="$(docker compose logs 2>&1 | grep -c 'PostgreSQL init process complete' || true)"
  if [ "$initialized" -ge 5 ]; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    docker compose ps
    echo "ERROR: базы не стали healthy за отведённое время"
    exit 1
  fi
  sleep 2
done

.venv/bin/python solution/db/check_databases.py
.venv/bin/pytest -q solution/tests
LLM_PROVIDER=mock .venv/bin/python solution/smoke_test.py --provider mock --require-execution

echo
echo "Setup завершён."
echo "Для обычной работы откройте START_TEXT2SQL.command двойным кликом"
echo "или выполните: ./start_app.sh"
echo "CLI для разработчика: ./run.sh"
