#!/bin/bash
# -----------------------------------------------------------------------------
# run_scheduler.sh
# Starts the server and activates the scheduler.
# Runs the simulation automatically every N minutes until CTRL+C.
#
# Usage:
#   ./run_scheduler.sh            # default: every 60 minutes
#   ./run_scheduler.sh 30         # every 30 minutes
# -----------------------------------------------------------------------------

set -e  # stop on any error

SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR"

# Activate virtual environment
source ../../venv_mock_data_catalogs/bin/activate

# Interval in minutes (first argument, default 60)
INTERVAL=${1:-60}

echo "========================================"
echo " Delivery Simulator — Scheduler Mode"
echo " Interval: every ${INTERVAL} minutes"
echo "========================================"

# Start server in background
echo "[1/2] Starting server..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!


# Wait for server to be ready
echo "[1/2] Waiting for server to be ready..."
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


# Activate the scheduler
echo "[2/2] Starting scheduler..."
curl -s -X POST "http://localhost:8000/simulate/scheduler/start?interval_minutes=${INTERVAL}"

echo ""
echo "✓ Server running with PID $SERVER_PID"
echo "  Docs:   http://localhost:8000/docs"
echo "  Events: http://localhost:8000/events"
echo ""
echo "  Press CTRL+C to stop."
echo ""

# Keep running until CTRL+C
trap "echo ''; echo 'Stopping scheduler...'; curl -s -X POST http://localhost:8000/simulate/scheduler/stop; echo 'Shutting down server...'; kill $SERVER_PID; echo '✓ Stopped.'; exit 0" SIGINT SIGTERM
wait $SERVER_PID