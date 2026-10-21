#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="default"
if [[ "${1:-}" == "--bookstack" ]]; then
  MODE="bookstack"
elif [[ -n "${1:-}" ]]; then
  echo "usage: scripts/demo.sh [--bookstack]" >&2
  exit 2
fi

STATE="$(mktemp -d "${TMPDIR:-/tmp}/shippy-demo.XXXXXX")"
PORT="$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
export SHIPPY_API_KEY="demo-key"
export SHIPPY_DEMO_CHROMA="$STATE/chroma"
export SHIPPY_DEMO_DB="$STATE/shippy.db"
export SHIPPY_DEMO_HOST="127.0.0.1"
export SHIPPY_DEMO_PORT="$PORT"
export BOOKSTACK_URL="${BOOKSTACK_URL:-http://localhost:8080}"
unset ASANA_PAT AWS_BEARER_TOKEN_BEDROCK SHIPPY_DEMO_LLM || true

SERVER_PID=""
cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$STATE"
}
trap cleanup EXIT

FAILED=0
BASE="http://127.0.0.1:$PORT"

pass() {
  echo "PASS $1"
}

fail() {
  echo "FAIL $1${2:+: $2}"
  FAILED=1
}

request() {
  local method=$1 path=$2 body=${3:-} key=${4:-}
  local args=(-sS -X "$method" -H "Content-Type: application/json" -w $'\n%{http_code}')
  if [[ -n "$key" ]]; then
    args+=(-H "x-api-key: $key")
  fi
  if [[ -n "$body" ]]; then
    args+=(-d "$body")
  fi
  curl "${args[@]}" "$BASE$path"
}

split_response() {
  local raw=$1
  HTTP_STATUS="${raw##*$'\n'}"
  HTTP_BODY="${raw%$'\n'*}"
}

show_body() {
  if [[ -n "$HTTP_BODY" ]]; then
    python3 -m json.tool <<<"$HTTP_BODY" 2>/dev/null || printf '%s\n' "$HTTP_BODY"
  fi
}

json_field() {
  python3 -c 'import json, sys; print(json.loads(sys.argv[1])[sys.argv[2]])' "$1" "$2"
}

wait_for_health() {
  local i
  for i in $(seq 1 120); do
    if curl -sf "$BASE/health" >/dev/null 2>&1; then
      return 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      return 1
    fi
    sleep 0.5
  done
  return 1
}

wait_for_bookstack() {
  local i code
  for i in $(seq 1 180); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$BOOKSTACK_URL/" || true)"
    if [[ "$code" =~ ^[23] ]]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

echo "Shippy v1 demo"
echo "mode: $MODE"
echo "state: $STATE"
echo "base: $BASE"
echo

if [[ "$MODE" == "bookstack" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required for --bookstack" >&2
    exit 2
  fi
  if [[ ! -f .env ]] || ! grep -q '^BOOKSTACK_TOKEN=..*' .env; then
    echo "--bookstack needs a .env with BOOKSTACK_TOKEN set (copy .env.example)" >&2
    exit 2
  fi
  echo "Starting BookStack with docker compose..."
  docker compose up -d
  wait_for_bookstack
  echo "Seeding the committed corpus into BookStack..."
  uv run python scripts/seed_bookstack.py
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  echo "Running live ingestion into the demo index..."
  SHIPPY_DEMO_BUILD_INDEX=0 PYTHONPATH="$ROOT" uv run python -c '
import os
from pathlib import Path
from shippy.ingest import main
raise SystemExit(main(path=Path(os.environ["SHIPPY_DEMO_CHROMA"])))
'
  export SHIPPY_DEMO_BUILD_INDEX=0
else
  export SHIPPY_DEMO_BUILD_INDEX=1
fi

echo "Starting the Shippy app with a deterministic mock LLM..."
PYTHONPATH="$ROOT" uv run python scripts/demo_app.py >"$STATE/server.log" 2>&1 &
SERVER_PID=$!

if ! wait_for_health; then
  echo "server failed to become healthy" >&2
  cat "$STATE/server.log" >&2 || true
  exit 1
fi

echo "--- server startup ---"
cat "$STATE/server.log"
echo

echo "=== Step 1: GET /health is open without a key ==="
split_response "$(request GET /health)"
echo "HTTP $HTTP_STATUS"
show_body
if [[ "$HTTP_STATUS" == "200" && "$HTTP_BODY" == '{"status":"ok"}' ]]; then
  pass "health open without key"
else
  fail "health open without key" "status=$HTTP_STATUS body=$HTTP_BODY"
fi
echo

echo "=== Step 2: POST /lookup with a wrong key is refused ==="
split_response "$(request POST /lookup '{"query":"How do we file a carrier claim for a damaged parcel?"}' wrong-key)"
echo "HTTP $HTTP_STATUS"
show_body
if [[ "$HTTP_STATUS" == "401" ]]; then
  pass "wrong key refused with 401"
else
  fail "wrong key refused with 401" "status=$HTTP_STATUS"
fi
echo

echo "=== Step 3: POST /lookup with the right key returns a cited answer ==="
CITED_BODY='{"query":"How do we file a carrier claim for a damaged parcel?"}'
split_response "$(request POST /lookup "$CITED_BODY" "$SHIPPY_API_KEY")"
echo "HTTP $HTTP_STATUS"
show_body
CITED_OK=0
if [[ "$HTTP_STATUS" == "200" ]]; then
  CITED_SOURCE="$(json_field "$HTTP_BODY" source_id 2>/dev/null || true)"
  CITED_ANSWER="$(json_field "$HTTP_BODY" answer 2>/dev/null || true)"
  CITED_QUOTE="$(json_field "$HTTP_BODY" quote 2>/dev/null || true)"
  if [[ "$CITED_SOURCE" == "sop-damaged-parcel-claims" && -n "$CITED_ANSWER" && -n "$CITED_QUOTE" ]]; then
    CITED_OK=1
  fi
fi
if [[ "$CITED_OK" == "1" ]]; then
  pass "cited answer with source_id and verbatim quote"
else
  fail "cited answer with source_id and verbatim quote" "status=$HTTP_STATUS"
fi
echo

echo "=== Step 4: unanswerable question returns a refusal with source links ==="
UNANSWERABLE_BODY='{"query":"What is the sick leave policy for warehouse staff?"}'
split_response "$(request POST /lookup "$UNANSWERABLE_BODY" "$SHIPPY_API_KEY")"
echo "HTTP $HTTP_STATUS"
show_body
UNANSWERABLE_OK=0
if [[ "$HTTP_STATUS" == "200" ]]; then
  UNANSWERABLE_REFUSED="$(json_field "$HTTP_BODY" refused 2>/dev/null || true)"
  UNANSWERABLE_LINKS="$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1]).get("source_links") or []))' "$HTTP_BODY" 2>/dev/null || echo 0)"
  if [[ "$UNANSWERABLE_REFUSED" == "True" && "$UNANSWERABLE_LINKS" -gt 0 ]]; then
    UNANSWERABLE_OK=1
  fi
fi
if [[ "$UNANSWERABLE_OK" == "1" ]]; then
  pass "unanswerable refusal with source links"
else
  fail "unanswerable refusal with source links" "status=$HTTP_STATUS"
fi
echo

echo "=== Step 5: trap query returns a refusal ==="
TRAP_BODY='{"query":"What is our restocking fee?"}'
split_response "$(request POST /lookup "$TRAP_BODY" "$SHIPPY_API_KEY")"
echo "HTTP $HTTP_STATUS"
show_body
TRAP_OK=0
if [[ "$HTTP_STATUS" == "200" ]]; then
  TRAP_REFUSED="$(json_field "$HTTP_BODY" refused 2>/dev/null || true)"
  TRAP_REASON="$(json_field "$HTTP_BODY" reason 2>/dev/null || true)"
  if [[ "$TRAP_REFUSED" == "True" && -n "$TRAP_REASON" ]]; then
    if [[ "$MODE" == "default" && "$TRAP_REASON" == *"version conflict"* ]]; then
      TRAP_OK=1
    elif [[ "$MODE" == "bookstack" ]]; then
      TRAP_OK=1
    fi
  fi
fi
if [[ "$TRAP_OK" == "1" ]]; then
  pass "trap query refused ($TRAP_REASON)"
else
  fail "trap query refused" "status=$HTTP_STATUS reason=${TRAP_REASON:-none}"
fi
echo

echo "=== Step 6: POST /workflows/run returns pending_approval ==="
WORKFLOW_PAYLOAD='{"action":"create_task","payload":{"title":"Chase the damaged parcel claim","description":"File the claim with the carrier.","project":"ops","sop_ref":"sop-damaged-parcel-claims"}}'
split_response "$(request POST /workflows/run "$WORKFLOW_PAYLOAD" "$SHIPPY_API_KEY")"
echo "HTTP $HTTP_STATUS"
show_body
RUN_ID=""
WORKFLOW_OK=0
if [[ "$HTTP_STATUS" == "200" ]]; then
  RUN_STATUS="$(json_field "$HTTP_BODY" status 2>/dev/null || true)"
  RUN_ID="$(json_field "$HTTP_BODY" run_id 2>/dev/null || true)"
  if [[ "$RUN_STATUS" == "pending_approval" && "$RUN_ID" == run-* ]]; then
    WORKFLOW_OK=1
  fi
fi
if [[ "$WORKFLOW_OK" == "1" ]]; then
  pass "workflow run pending_approval ($RUN_ID)"
else
  fail "workflow run pending_approval" "status=$HTTP_STATUS"
fi
echo

echo "=== Step 7: approve completes the run with a fallback task ==="
APPROVE_OK=0
TASK_MODE=""
if [[ -n "$RUN_ID" ]]; then
  split_response "$(request POST "/workflows/$RUN_ID/approve" "" "$SHIPPY_API_KEY")"
  echo "HTTP $HTTP_STATUS"
  show_body
  if [[ "$HTTP_STATUS" == "200" ]]; then
    APPROVE_STATUS="$(json_field "$HTTP_BODY" status 2>/dev/null || true)"
    TASK_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("task", {}).get("mode", ""))' "$HTTP_BODY" 2>/dev/null || true)"
    if [[ "$APPROVE_STATUS" == "completed" && "$TASK_MODE" == "fallback" ]]; then
      APPROVE_OK=1
    fi
  fi
else
  echo "skipped: no run_id from step 6"
fi
if [[ "$APPROVE_OK" == "1" ]]; then
  pass "approve completed with fallback task"
else
  fail "approve completed with fallback task" "status=${HTTP_STATUS:-n/a}"
fi
echo

echo "=== Step 8: GET /runs/{id} returns the full audit trail in order ==="
TRAIL_OK=0
if [[ -n "$RUN_ID" ]]; then
  split_response "$(request GET "/runs/$RUN_ID" "" "$SHIPPY_API_KEY")"
  echo "HTTP $HTTP_STATUS"
  show_body
  if [[ "$HTTP_STATUS" == "200" ]]; then
    TRAIL_EVENTS="$(python3 -c 'import json,sys; print(",".join(e["event"] for e in json.loads(sys.argv[1])["events"]))' "$HTTP_BODY" 2>/dev/null || true)"
    TRAIL_SEQS="$(python3 -c 'import json,sys; print([e["seq"] for e in json.loads(sys.argv[1])["events"]])' "$HTTP_BODY" 2>/dev/null || true)"
    if [[ "$TRAIL_EVENTS" == "run_created,approved,task_created" ]]; then
      TRAIL_OK=1
    fi
  fi
else
  echo "skipped: no run_id from step 6"
fi
if [[ "$TRAIL_OK" == "1" ]]; then
  pass "audit trail in order: $TRAIL_EVENTS (seq $TRAIL_SEQS)"
else
  fail "audit trail in order" "status=${HTTP_STATUS:-n/a}"
fi
echo

echo "=== Summary ==="
if [[ "$FAILED" == "0" ]]; then
  echo "DEMO PASSED (8/8 steps)"
  exit 0
fi
echo "DEMO FAILED"
exit 1
