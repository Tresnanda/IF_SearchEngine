#!/usr/bin/env bash
set -euo pipefail

cleanup() {
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose up -d --build

for i in {1..40}; do
  backend_id="$(docker compose ps -q backend)"
  frontend_id="$(docker compose ps -q frontend)"

  backend_status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$backend_id")"
  frontend_status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$frontend_id")"

  if [[ "$backend_status" == "healthy" && "$frontend_status" == "healthy" ]]; then
    echo "healthy"
    exit 0
  fi

  sleep 3
done

echo "services did not become healthy in time"
docker compose ps || true
exit 1
