#!/bin/bash
#SBATCH --partition=MGPU-TC2
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#
### Specify Memory allocate to this job ###
#SBATCH --mem=1G
#
### Specify number of core (CPU) to allocate to per task ###
#SBATCH --cpus-per-task=1
#
### Specify number of node to compute ###
#SBATCH --nodes=1
#
### Optional: Specify node to execute the job ###
### Remove 1st # at next line for the option to take effect ###
##SBATCH --nodelist=TC2N01
#
### Specify Time Limit, format: <min> or <min>:<sec> or <hr>:<min>:<sec> or <days>-<hr>:<min>:<sec> or <days>-<hr> ###
#SBATCH --time=30
#
### Specify name for the job, filename format for output and error ###
#SBATCH --job-name=TestJob
#SBATCH --output=output_%x_%j.out
#SBATCH --error=error_%x_%j.err

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Picking a free port from server with a high number (incase HPC locked 1025)
# Woohoo for myself that let run_script able to pick a port in flags!
pick_port() {
  python - <<'PY'
import random, socket
low, high = 20000, 40000
for _ in range(200):
    port = random.randint(low, high)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)
raise SystemExit(1)
PY
}

PORT="$(pick_port)"
echo "Using port: $PORT"

# Define cleanup function to stop the server on exit
cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" || true
    wait "$SERVER_PID" || true
  fi
}
trap cleanup EXIT

echo "Starting LLM server..."
"$ROOT/script/run_qwen3vl_server.sh" "$PORT" &
SERVER_PID=$!

# Wait for server to be ready (Health check)
python - <<PY
import socket, time, sys
port = int("$PORT")
deadline = time.time() + 30
while time.time() < deadline:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        sys.exit(0)
    except OSError:
        time.sleep(0.5)
    finally:
        try:
            s.close()
        except Exception:
            pass
sys.exit(1)
PY

# Envs
export LLM_PORT="$PORT"
export LLM_BASE_URL="http://127.0.0.1:$PORT/v1"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

# Determine which python command (I 'm testing command availability here)')
if command -v uv >/dev/null 2>&1; then
  PY_CMD=(uv run python)
elif command -v python >/dev/null 2>&1; then
  PY_CMD=(python)
elif command -v python3 >/dev/null 2>&1; then
  PY_CMD=(python3)
else
  echo "No python found in PATH."
  exit 1
fi

# Finally start evaluation pipeline
echo "Running ReAct FEVER eval..."
"${PY_CMD[@]}" "$ROOT/src/react-based-method/run_skill_fever_eval.py" \
  --split dev \
  --n 20 \
  --data-dir "$ROOT/data" \
  --base-url "http://127.0.0.1:$PORT"

# Algorithms are FUN!
