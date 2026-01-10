#!/bin/bash
# OpsConductor v2 Restart Script
# Stops all services, applies configuration from database, and restarts

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Use full paths for Python tools
CELERY="/home/opsconductor/.local/bin/celery"
UVICORN="/home/opsconductor/.local/bin/uvicorn"
NPM="/snap/bin/npm"
PYTHON="/usr/bin/python3"

echo "=== OpsConductor v2 Restart ==="
echo "[*] Reading configuration from database..."

# Read polling configuration from database
read_setting() {
    local key=$1
    local default=$2
    local value=$($PYTHON -c "
import psycopg2
import os
conn = psycopg2.connect(
    host=os.environ.get('PG_HOST', 'localhost'),
    port=os.environ.get('PG_PORT', '5432'),
    database=os.environ.get('PG_DATABASE', 'opsconductor_v2'),
    user=os.environ.get('PG_USER', 'postgres'),
    password=os.environ.get('PG_PASSWORD', 'postgres')
)
cur = conn.cursor()
cur.execute('SELECT value FROM system_settings WHERE key = %s', ('$key',))
row = cur.fetchone()
print(row[0] if row else '$default')
conn.close()
" 2>/dev/null || echo "$default")
    echo "$value"
}

WORKER_COUNT=$(read_setting "polling_worker_count" "1")
WORKER_CONCURRENCY=$(read_setting "polling_worker_concurrency" "4")
RATE_LIMIT=$(read_setting "polling_rate_limit" "100")
POLL_INTERVAL=$(read_setting "polling_interval" "60")

echo "[✓] Configuration loaded:"
echo "    Workers: $WORKER_COUNT"
echo "    Concurrency: $WORKER_CONCURRENCY"
echo "    Rate Limit: $RATE_LIMIT/s"
echo "    Poll Interval: ${POLL_INTERVAL}s"

# Stop all services
echo "[*] Stopping services..."
"$PROJECT_DIR/stop.sh" 2>/dev/null || true

# Wait for processes to fully stop
sleep 2

# Create logs directory
mkdir -p logs

# Clear Python bytecode cache
echo "[*] Clearing caches..."
find "$PROJECT_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true
rm -f celerybeat-schedule celerybeat-schedule.db celerybeat.pid 2>/dev/null || true

# Update celery_app.py with new rate limit (dynamic)
# Note: Rate limit is set per-task, so we update it via environment variable
export POLLING_RATE_LIMIT="$RATE_LIMIT/s"

# Start Celery Workers (based on worker_count setting)
echo "[*] Starting $WORKER_COUNT Celery Worker(s) with concurrency=$WORKER_CONCURRENCY..."
for i in $(seq 1 $WORKER_COUNT); do
    nohup $CELERY -A backend.tasks.celery_app worker -l info \
        --concurrency=$WORKER_CONCURRENCY \
        -Q celery,dispatch,polling,maintenance \
        -n worker${i}@%h \
        > logs/celery-worker-${i}.log 2>&1 &
    
    if [ $i -eq 1 ]; then
        echo $! > logs/celery-worker.pid
    fi
    echo "[✓] Worker $i started (PID: $!)"
done

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
echo "=== Restart Complete ==="
echo "  Backend:  http://localhost:5001"
echo "  Frontend: http://localhost:3000"
echo "  Workers:  $WORKER_COUNT × $WORKER_CONCURRENCY = $((WORKER_COUNT * WORKER_CONCURRENCY)) parallel polls"
echo "  Rate:     $RATE_LIMIT polls/second max"
