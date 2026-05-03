#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="$ROOT_DIR/.run"
STATE_FILE="$LOG_DIR/local-flow.env"
ADMIN_PORT="${ADMIN_PORT:-6000}"
GATEWAY_PORT="${GATEWAY_PORT:-6001}"
MILVUS_HOST="${MILVUS_HOST:-127.0.0.1}"
MILVUS_PORT="${MILVUS_PORT:-19530}"
MILVUS_ALIAS="${MILVUS_ALIAS:-default}"
MILVUS_DB_NAME="${MILVUS_DB_NAME:-Canary}"
MILVUS_IMAGE="${MILVUS_IMAGE:-milvusdb/milvus:v2.3.12}"
ETCD_IMAGE="${ETCD_IMAGE:-quay.io/coreos/etcd:v3.5.5}"
MINIO_IMAGE="${MINIO_IMAGE:-minio/minio:RELEASE.2023-03-20T20-16-18Z}"
KEEP_SERVICES_UP="${KEEP_SERVICES_UP:-0}"
SKIP_SMOKE="${SKIP_SMOKE:-0}"
STARTED_COMPOSE=0

mkdir -p "$LOG_DIR"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose is required but not found" >&2
  exit 1
fi

cleanup() {
  local exit_code=$?
  if [[ "$KEEP_SERVICES_UP" != "1" ]]; then
    if [[ -f "$LOG_DIR/admin.pid" ]]; then
      kill "$(cat "$LOG_DIR/admin.pid")" >/dev/null 2>&1 || true
      rm -f "$LOG_DIR/admin.pid"
    fi
    if [[ -f "$LOG_DIR/gateway.pid" ]]; then
      kill "$(cat "$LOG_DIR/gateway.pid")" >/dev/null 2>&1 || true
      rm -f "$LOG_DIR/gateway.pid"
    fi
    rm -f "$STATE_FILE"
  fi
  if [[ "${KEEP_MILVUS_UP:-0}" != "1" && "$STARTED_COMPOSE" == "1" ]]; then
    "${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.milvus.yml" down >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}

trap cleanup EXIT

echo "[1/6] install python dependencies"
python3 -m pip install -r "$BACKEND_DIR/requirements-dev.txt" >/dev/null

wait_for_milvus_port() {
  python3 - <<'PY'
from __future__ import annotations

import os
import socket
import time

host = os.environ.get("MILVUS_HOST", "127.0.0.1")
port = int(os.environ.get("MILVUS_PORT", "19530"))
deadline = time.time() + 180

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"milvus ready at {host}:{port}")
            raise SystemExit(0)
    except OSError:
        time.sleep(2)

raise SystemExit("milvus did not become ready in time")
PY
}

is_port_open() {
  local port="$1"
  python3 - "$port" <<'PY'
from __future__ import annotations

import socket
import sys

port = int(sys.argv[1])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.5)
    code = sock.connect_ex(("127.0.0.1", port))
    raise SystemExit(0 if code == 0 else 1)
PY
}

stop_managed_process() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$pid_file"
}

ensure_port_available() {
  local port="$1"
  local service_name="$2"
  if is_port_open "$port"; then
    echo "${service_name} port is already in use: ${port}" >&2
    exit 1
  fi
}

start_detached_service() {
  local module_path="$1"
  local port="$2"
  local log_file="$3"
  local pid_file="$4"

  python3 - \
    "$BACKEND_DIR" \
    "$module_path" \
    "$port" \
    "$log_file" \
    "$pid_file" \
    "$MILVUS_HOST" \
    "$MILVUS_PORT" \
    "$MILVUS_ALIAS" \
    "$MILVUS_DB_NAME" <<'PY'
from __future__ import annotations

import subprocess
import sys

backend_dir, module_path, port, log_file, pid_file, milvus_host, milvus_port, milvus_alias, milvus_db_name = sys.argv[1:]

env = dict(__import__("os").environ)
env.update(
    {
        "PYTHONPATH": backend_dir,
        "CANARY_REPOSITORY_BACKEND": "milvus",
        "MILVUS_HOST": milvus_host,
        "MILVUS_PORT": milvus_port,
        "MILVUS_ALIAS": milvus_alias,
        "MILVUS_DB_NAME": milvus_db_name,
    }
)

with open(log_file, "ab") as log_fp:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            module_path,
            "--host",
            "127.0.0.1",
            "--port",
            port,
        ],
        cwd=backend_dir,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

with open(pid_file, "w", encoding="utf-8") as pid_fp:
    pid_fp.write(str(process.pid))
PY
}

echo "[2/6] ensure Milvus is available"
if python3 - <<'PY'
from __future__ import annotations

import os
import socket

host = os.environ.get("MILVUS_HOST", "127.0.0.1")
port = int(os.environ.get("MILVUS_PORT", "19530"))

try:
    with socket.create_connection((host, port), timeout=2):
        raise SystemExit(0)
except OSError:
    raise SystemExit(1)
PY
then
  echo "reuse existing Milvus at ${MILVUS_HOST}:${MILVUS_PORT}"
else
  echo "start Milvus via docker compose using local images only"
  ETCD_IMAGE="$ETCD_IMAGE" MINIO_IMAGE="$MINIO_IMAGE" MILVUS_IMAGE="$MILVUS_IMAGE" \
    "${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.milvus.yml" up -d
  STARTED_COMPOSE=1
fi

echo "[3/6] wait for Milvus health"
wait_for_milvus_port

echo "[4/6] initialize Canary database and collections"
PYTHONPATH="$ROOT_DIR" \
MILVUS_HOST="$MILVUS_HOST" \
MILVUS_PORT="$MILVUS_PORT" \
MILVUS_ALIAS="$MILVUS_ALIAS" \
MILVUS_DB_NAME="$MILVUS_DB_NAME" \
python3 "$ROOT_DIR/scripts/init_milvus_canary.py"

echo "[5/6] start admin and gateway api"
stop_managed_process "$LOG_DIR/admin.pid"
stop_managed_process "$LOG_DIR/gateway.pid"
ensure_port_available "$ADMIN_PORT" "admin_api"
ensure_port_available "$GATEWAY_PORT" "gateway_api"
echo "admin_api port:   $ADMIN_PORT"
echo "gateway_api port: $GATEWAY_PORT"
start_detached_service "apps.admin_api.main:app" "$ADMIN_PORT" "$LOG_DIR/admin.log" "$LOG_DIR/admin.pid"
start_detached_service "apps.gateway_api.main:app" "$GATEWAY_PORT" "$LOG_DIR/gateway.log" "$LOG_DIR/gateway.pid"

wait_for_http() {
  local url="$1"
  local name="$2"
  local deadline=$((SECONDS + 90))
  while (( SECONDS < deadline )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name ready: $url"
      return 0
    fi
    sleep 2
  done
  echo "$name failed to become healthy: $url" >&2
  return 1
}

wait_for_http "http://127.0.0.1:${ADMIN_PORT}/canary" "admin_api"
wait_for_http "http://127.0.0.1:${GATEWAY_PORT}/canary" "gateway_api"

cat >"$STATE_FILE" <<EOF
ADMIN_PORT=$ADMIN_PORT
GATEWAY_PORT=$GATEWAY_PORT
ADMIN_BASE_URL=http://127.0.0.1:${ADMIN_PORT}
GATEWAY_BASE_URL=http://127.0.0.1:${GATEWAY_PORT}
EOF

if [[ "$SKIP_SMOKE" == "1" ]]; then
  echo "[6/6] skip smoke test (SKIP_SMOKE=1)"
else
  echo "[6/6] run smoke test"
  PYTHONPATH="$ROOT_DIR" \
  ADMIN_BASE_URL="http://127.0.0.1:${ADMIN_PORT}" \
  GATEWAY_BASE_URL="http://127.0.0.1:${GATEWAY_PORT}" \
  python3 "$ROOT_DIR/scripts/smoke_test_canary.py"
fi

echo
echo "local Milvus flow passed"
echo "admin log:   $LOG_DIR/admin.log"
echo "gateway log: $LOG_DIR/gateway.log"
echo "admin url:   http://127.0.0.1:${ADMIN_PORT}/canary"
echo "gateway url: http://127.0.0.1:${GATEWAY_PORT}/canary"
if [[ "$SKIP_SMOKE" == "1" ]]; then
  echo "smoke mode:  skipped"
else
  echo "smoke mode:  enabled"
fi

if [[ "$KEEP_SERVICES_UP" == "1" ]]; then
  echo
  echo "services are still running for local debugging"
  echo "admin docs:  http://127.0.0.1:${ADMIN_PORT}/canary/docs"
  echo "gateway docs: http://127.0.0.1:${GATEWAY_PORT}/canary/docs"
  echo "state file:  $STATE_FILE"
  echo "stop with:   make local-flow-stop"
fi
