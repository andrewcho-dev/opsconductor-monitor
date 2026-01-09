#!/bin/bash
# Full OpsConductor Restart Script
# Clears all caches and restarts all services
# Usage: sudo ./scripts/full-restart.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "OpsConductor Full Restart"
echo "=========================================="

# 1. Stop all services
echo "🛑 Stopping all services..."
systemctl stop opsconductor-backend.service 2>/dev/null || true
systemctl stop opsconductor-celery.service 2>/dev/null || true
systemctl stop opsconductor-beat.service 2>/dev/null || true
systemctl stop opsconductor-worker.service 2>/dev/null || true

# 2. Kill any stray processes
echo "🔪 Killing stray processes..."
pkill -9 -f "uvicorn.*app:app" 2>/dev/null || true
pkill -9 -f "celery.*worker" 2>/dev/null || true
pkill -9 -f "celery.*beat" 2>/dev/null || true
sleep 2

# 3. Clear Python cache
echo "🧹 Clearing Python cache..."
find "$PROJECT_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true

# 4. Clear Celery cache (if using file-based)
echo "🧹 Clearing Celery cache..."
rm -rf /tmp/celery* 2>/dev/null || true

# 5. Flush Redis cache (optional - uncomment if needed)
# echo "🧹 Flushing Redis cache..."
# redis-cli FLUSHALL 2>/dev/null || true

# 6. Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# 7. Restart nginx
echo "🌐 Restarting nginx..."
systemctl restart nginx

# 8. Start backend
echo "🚀 Starting backend..."
systemctl start opsconductor-backend.service
sleep 3

# 9. Start Celery workers
echo "🚀 Starting Celery workers..."
systemctl start opsconductor-celery.service 2>/dev/null || systemctl start opsconductor-worker.service 2>/dev/null || true
sleep 2

# 10. Start Celery beat
echo "🚀 Starting Celery beat..."
systemctl start opsconductor-beat.service 2>/dev/null || true

# 11. Verify services
echo ""
echo "=========================================="
echo "Service Status"
echo "=========================================="
systemctl status opsconductor-backend.service --no-pager -l | head -5
echo ""
systemctl status opsconductor-celery.service --no-pager -l 2>/dev/null | head -5 || systemctl status opsconductor-worker.service --no-pager -l 2>/dev/null | head -5 || echo "Celery: not found"
echo ""
systemctl status nginx --no-pager -l | head -5

echo ""
echo "=========================================="
echo "✅ Full restart complete!"
echo "=========================================="
echo ""
echo "Clear browser cache (Ctrl+Shift+R) to see frontend changes."
echo ""
