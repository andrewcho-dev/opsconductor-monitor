#!/bin/bash
# OpsConductor v2 Development Status Script
# Shows status of all services

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== OpsConductor v2 Service Status ==="
echo ""

# Check Redis
if pgrep -x redis-server > /dev/null; then
    echo "[✓] Redis:         running"
else
    echo "[✗] Redis:         NOT running"
fi

# Check PostgreSQL
if pgrep -x postgres > /dev/null; then
    echo "[✓] PostgreSQL:    running"
else
    echo "[✗] PostgreSQL:    NOT running"
fi

echo ""

# Check Celery Worker
if [ -f logs/celery-worker.pid ]; then
    PID=$(cat logs/celery-worker.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "[✓] Celery Worker: running (PID: $PID)"
    else
        echo "[✗] Celery Worker: NOT running (stale PID file)"
    fi
else
    # Check if running without PID file
    PIDS=$(pgrep -f "celery.*backend.tasks.*worker" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "[?] Celery Worker: running (PID: $PIDS) - no PID file"
    else
        echo "[✗] Celery Worker: NOT running"
    fi
fi

# Check Celery Beat
if [ -f logs/celery-beat.pid ]; then
    PID=$(cat logs/celery-beat.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "[✓] Celery Beat:   running (PID: $PID)"
    else
        echo "[✗] Celery Beat:   NOT running (stale PID file)"
    fi
else
    PIDS=$(pgrep -f "celery.*backend.tasks.*beat" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "[?] Celery Beat:   running (PID: $PIDS) - no PID file"
    else
        echo "[✗] Celery Beat:   NOT running"
    fi
fi

# Check Backend
if [ -f logs/backend.pid ]; then
    PID=$(cat logs/backend.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "[✓] Backend:       running (PID: $PID) - http://localhost:5001"
    else
        echo "[✗] Backend:       NOT running (stale PID file)"
    fi
else
    PIDS=$(pgrep -f "uvicorn.*backend.api.main" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "[?] Backend:       running (PID: $PIDS) - no PID file"
    else
        echo "[✗] Backend:       NOT running"
    fi
fi

# Check Frontend
if [ -f logs/frontend.pid ]; then
    PID=$(cat logs/frontend.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "[✓] Frontend:      running (PID: $PID) - http://localhost:3000"
    else
        echo "[✗] Frontend:      NOT running (stale PID file)"
    fi
else
    PIDS=$(pgrep -f "vite.*3000" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "[?] Frontend:      running (PID: $PIDS) - no PID file"
    else
        echo "[✗] Frontend:      NOT running"
    fi
fi

echo ""
echo "Logs: $PROJECT_DIR/logs/"
