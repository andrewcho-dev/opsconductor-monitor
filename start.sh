#!/bin/bash
# OpsConductor v2 Development Start Script
# Starts all services in the correct order

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Use full paths for Python tools
CELERY="/home/opsconductor/.local/bin/celery"
UVICORN="/home/opsconductor/.local/bin/uvicorn"
NPM="/snap/bin/npm"

echo "=== OpsConductor v2 Development Start ==="

# Check Redis
if ! pgrep -x redis-server > /dev/null; then
    echo "[!] Redis is not running. Please start Redis first:"
    echo "    sudo systemctl start redis-server"
    exit 1
fi
echo "[✓] Redis is running"

# Check PostgreSQL
if ! pgrep -x postgres > /dev/null; then
    echo "[!] PostgreSQL is not running. Please start PostgreSQL first:"
    echo "    sudo systemctl start postgresql"
    exit 1
fi
echo "[✓] PostgreSQL is running"

# Create logs directory
mkdir -p logs

# Clear Python bytecode cache before starting (prevents stale code issues)
echo "[*] Clearing Python bytecode cache..."
find "$PROJECT_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true

# Clear celerybeat schedule to ensure fresh start
rm -f celerybeat-schedule celerybeat-schedule.db celerybeat.pid 2>/dev/null || true
echo "[✓] Caches cleared"

# Start Celery Worker (handles all queues: dispatch, polling, maintenance)
# For production with 2000+ devices, run separate workers for each queue
echo "[*] Starting Celery Worker..."
cd "$PROJECT_DIR"
nohup $CELERY -A backend.tasks.celery_app worker -l info --concurrency=4 \
    -Q celery,dispatch,polling,maintenance \
    -n worker@%h \
    > logs/celery-worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > logs/celery-worker.pid
echo "[✓] Celery Worker started (PID: $WORKER_PID)"
echo "    Queues: celery, dispatch, polling, maintenance"

# Start Celery Beat
echo "[*] Starting Celery Beat..."
nohup $CELERY -A backend.tasks.celery_app beat -l info \
    > logs/celery-beat.log 2>&1 &
BEAT_PID=$!
echo $BEAT_PID > logs/celery-beat.pid
echo "[✓] Celery Beat started (PID: $BEAT_PID)"

# Start Flower (Celery monitoring)
echo "[*] Starting Flower on port 5555..."
nohup $CELERY -A backend.tasks.celery_app flower --port=5555 --address=0.0.0.0 \
    > logs/flower.log 2>&1 &
FLOWER_PID=$!
echo $FLOWER_PID > logs/flower.pid
echo "[✓] Flower started (PID: $FLOWER_PID) - http://localhost:5555"

# Start FastAPI Backend
echo "[*] Starting FastAPI Backend on port 5001..."
nohup $UVICORN backend.api.main:app --host 0.0.0.0 --port 5001 --reload \
    > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid
echo "[✓] Backend started (PID: $BACKEND_PID)"

# Start Frontend
echo "[*] Starting Frontend on port 3000..."
cd "$PROJECT_DIR/frontend"
nohup $NPM run dev -- --port 3000 --host 0.0.0.0 \
    > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid
echo "[✓] Frontend started (PID: $FRONTEND_PID)"

cd "$PROJECT_DIR"

echo ""
echo "=== All Services Started ==="
echo "  Backend:  http://localhost:5001"
echo "  Frontend: http://localhost:3000"
echo "  Logs:     $PROJECT_DIR/logs/"
echo ""
echo "To stop all services: ./stop.sh"
