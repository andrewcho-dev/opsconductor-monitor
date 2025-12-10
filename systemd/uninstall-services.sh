#!/bin/bash
# Uninstall OpsConductor systemd services
# Run with: sudo ./uninstall-services.sh

set -e

echo "🛑 Stopping and removing OpsConductor systemd services..."

# Stop services
systemctl stop opsconductor-beat 2>/dev/null || true
systemctl stop opsconductor-worker 2>/dev/null || true
systemctl stop opsconductor-backend 2>/dev/null || true

# Disable services
systemctl disable opsconductor-beat 2>/dev/null || true
systemctl disable opsconductor-worker 2>/dev/null || true
systemctl disable opsconductor-backend 2>/dev/null || true

# Remove service files
rm -f /etc/systemd/system/opsconductor-backend.service
rm -f /etc/systemd/system/opsconductor-worker.service
rm -f /etc/systemd/system/opsconductor-beat.service

# Reload systemd
systemctl daemon-reload

echo "✅ Services removed. You can now use ./start.sh for development."
