#!/bin/bash
# Install OpsConductor systemd services
# Run with: sudo ./install-services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📦 Installing OpsConductor systemd services..."

# Stop existing dev processes
echo "🛑 Stopping any dev processes..."
pkill -9 -f "python.*app.py" 2>/dev/null || true
pkill -9 -f "celery.*worker" 2>/dev/null || true
pkill -9 -f "celery.*beat" 2>/dev/null || true
lsof -ti:5000 | xargs -r kill -9 2>/dev/null || true
sleep 2

# Copy service files
echo "📋 Copying service files to /etc/systemd/system/..."
cp "$SCRIPT_DIR/opsconductor-backend.service" /etc/systemd/system/
cp "$SCRIPT_DIR/opsconductor-worker.service" /etc/systemd/system/
cp "$SCRIPT_DIR/opsconductor-beat.service" /etc/systemd/system/

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable services (start on boot)
echo "✅ Enabling services to start on boot..."
systemctl enable opsconductor-backend
systemctl enable opsconductor-worker
systemctl enable opsconductor-beat

# Start services
echo "🚀 Starting services..."
systemctl start opsconductor-backend
sleep 3
systemctl start opsconductor-worker
sleep 2
systemctl start opsconductor-beat

echo ""
echo "=========================================="
echo "OpsConductor services installed!"
echo "=========================================="
echo ""
echo "Commands:"
echo "  Status:  sudo systemctl status opsconductor-backend opsconductor-worker opsconductor-beat"
echo "  Logs:    sudo journalctl -u opsconductor-backend -f"
echo "  Restart: sudo systemctl restart opsconductor-backend"
echo "  Stop:    sudo systemctl stop opsconductor-backend opsconductor-worker opsconductor-beat"
echo ""
echo "Backend: http://192.168.10.50:5000"
echo ""
