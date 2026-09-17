#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Desktop не установлен: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Запускаю Docker Desktop..."
  [[ "$(uname -s)" == "Darwin" ]] && open -a "Docker" || true
  for _attempt in $(seq 1 60); do
    docker info >/dev/null 2>&1 && break
    sleep 2
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker не запустился. Откройте Docker Desktop и повторите."
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  ./setup.sh
else
  docker compose up -d
fi

for _attempt in $(seq 1 60); do
  .venv/bin/python solution/db/check_databases.py >/dev/null 2>&1 && exit 0
  sleep 2
done

echo "Базы данных не готовы. Проверьте Docker Desktop."
exit 1
