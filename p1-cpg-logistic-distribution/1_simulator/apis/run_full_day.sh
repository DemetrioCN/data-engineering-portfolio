#!/bin/bash
# -----------------------------------------------------------------------------
# run_batch.sh
# Runs the simulation repeatedly until all routes are exhausted.
# -----------------------------------------------------------------------------

set -e

SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR"

source ../../venv_mock_data_catalogs/bin/activate

echo "========================================"
echo " Delivery Simulator — Batch Mode"
echo "========================================"

# Start server
echo "[1/3] Starting server..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

trap "echo 'Shutting down...'; kill $SERVER_PID; exit 0" SIGINT SIGTERM

# Wait for server
echo "[2/3] Waiting for server to be ready..."
for i in {1..15}; do
    curl -s http://localhost:8000/docs > /dev/null && break
    echo "  Retrying... ($i/15)"
    sleep 1
done

if ! curl -s http://localhost:8000/docs > /dev/null; then
    echo "✗ Server did not start. Aborting."
    kill $SERVER_PID
    exit 1
fi

# Run in loop until no events are generated
echo "[3/3] Running batch simulation..."
RUN=1
TOTAL=0

while true; do
    echo ""
    echo "--- Run $RUN ---"
    RESPONSE=$(curl -s -X POST http://localhost:8000/simulate/batch)
    COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

    echo "  Events generated: $COUNT"
    TOTAL=$((TOTAL + COUNT))

    if [ "$COUNT" -eq 0 ]; then
        echo ""
        echo "  No more pending visits — all routes exhausted."
        break
    fi

    RUN=$((RUN + 1))
done

echo ""
kill $SERVER_PID
echo "✓ Done. Total events: $TOTAL"
echo "  Output: ../data/data_events/visit_list/"