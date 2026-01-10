#!/bin/bash
# OpsConductor v2 Development Stop Script
# Stops all services gracefully

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== OpsConductor v2 Development Stop ==="

# Function to kill process and wait
kill_and_wait() {
    local PID=$1
    local NAME=$2
    if kill -0 $PID 2>/dev/null; then
        echo "[*] Stopping $NAME (PID: $PID)..."
        kill $PID 2>/dev/null
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 $PID 2>/dev/null; then
                echo "[✓] $NAME stopped"
                return 0
            fi
            sleep 0.5
        done
        # Force kill if still running
        echo "[*] Force killing $NAME..."
        kill -9 $PID 2>/dev/null || true
        echo "[✓] $NAME stopped (forced)"
    fi
}

# Stop Frontend
if [ -f logs/frontend.pid ]; then
    PID=$(cat logs/frontend.pid)
    kill_and_wait $PID "Frontend"
    rm -f logs/frontend.pid
fi

# Stop Backend
if [ -f logs/backend.pid ]; then
    PID=$(cat logs/backend.pid)
    kill_and_wait $PID "Backend"
    rm -f logs/backend.pid
fi

# Stop Flower
if [ -f logs/flower.pid ]; then
    PID=$(cat logs/flower.pid)
    kill_and_wait $PID "Flower"
    rm -f logs/flower.pid
fi

# Stop Celery Beat
if [ -f logs/celery-beat.pid ]; then
    PID=$(cat logs/celery-beat.pid)
    kill_and_wait $PID "Celery Beat"
    rm -f logs/celery-beat.pid
fi

# Stop Celery Worker
if [ -f logs/celery-worker.pid ]; then
    PID=$(cat logs/celery-worker.pid)
    kill_and_wait $PID "Celery Worker"
    rm -f logs/celery-worker.pid
fi

# Kill any remaining processes for this project
echo "[*] Cleaning up any remaining processes..."
pkill -9 -f "celery.*backend.tasks" 2>/dev/null || true
pkill -9 -f "uvicorn.*backend.api.main" 2>/dev/null || true
pkill -9 -f "node.*vite.*3000" 2>/dev/null || true

# Clean up celerybeat schedule files
echo "[*] Clearing Celery beat schedule..."
rm -f celerybeat-schedule celerybeat-schedule.db celerybeat.pid 2>/dev/null || true

# Clear Python bytecode cache to prevent stale code issues
echo "[*] Clearing Python bytecode cache..."
find "$PROJECT_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true

# Clear any .pytest_cache
rm -rf "$PROJECT_DIR/.pytest_cache" 2>/dev/null || true

echo ""
echo "=== All Services Stopped and Caches Cleared ==="
