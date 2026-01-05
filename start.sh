#!/bin/bash
# OpsConductor Monitor - Startup Script
# Handles clean startup of backend, workers, and frontend

set -e
cd "$(dirname "$0")"

echo "🔄 Stopping any existing processes..."

# Kill existing processes cleanly
pkill -9 -f "uvicorn.*app:app" 2>/dev/null || true
pkill -9 -f "python.*app.py" 2>/dev/null || true
pkill -9 -f "celery.*worker" 2>/dev/null || true
pkill -9 -f "celery.*beat" 2>/dev/null || true
lsof -ti:5000 | xargs -r kill -9 2>/dev/null || true
sleep 2

echo "🚀 Starting FastAPI backend on port 5000..."
nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 5000 --reload > /tmp/opsconductor_backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

# Verify backend started
if curl -s -m 5 "http://127.0.0.1:5000/api/health" > /dev/null 2>&1; then
    echo "✅ Backend started (PID: $BACKEND_PID)"
else
    echo "❌ Backend failed to start. Check /tmp/opsconductor_backend.log"
    cat /tmp/opsconductor_backend.log | tail -20
    exit 1
fi

echo "🚀 Starting Celery worker..."
# Single worker with 32 processes - chord tasks distribute across all processes
CPU_COUNT=$(nproc 2>/dev/null || echo 4)
CONCURRENCY=$((CPU_COUNT * 2))
if [ $CONCURRENCY -gt 32 ]; then CONCURRENCY=32; fi
echo "   1 worker × $CONCURRENCY processes (based on $CPU_COUNT cores)"
nohup python3 -m celery -A celery_app worker -l info --concurrency=$CONCURRENCY --prefetch-multiplier=1 -n worker1@%h > /tmp/opsconductor_worker.log 2>&1 &
WORKER_PID=$!
sleep 2
echo "✅ Celery worker started (PID: $WORKER_PID)"

echo "🚀 Starting Celery beat scheduler..."
nohup python3 -m celery -A celery_app beat -l info > /tmp/opsconductor_beat.log 2>&1 &
BEAT_PID=$!
sleep 1
echo "✅ Celery beat started (PID: $BEAT_PID)"

echo ""
echo "=========================================="
echo "OpsConductor Monitor is running!"
echo "=========================================="
echo "Backend:  http://192.168.10.50:5000"
echo "Frontend: http://192.168.10.50:3000 (start separately with: cd frontend && npm run dev)"
echo ""
echo "Logs:"
echo "  Backend: /tmp/opsconductor_backend.log"
echo "  Worker:  /tmp/opsconductor_worker.log"
echo "  Beat:    /tmp/opsconductor_beat.log"
echo ""
echo "To stop: ./stop.sh"
