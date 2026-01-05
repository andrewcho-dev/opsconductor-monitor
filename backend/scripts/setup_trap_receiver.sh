#!/bin/bash
# Setup script for SNMP Trap Receiver
# This script installs the systemd service and configures permissions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$PROJECT_DIR/services/snmp-trap-receiver.service"

echo "=== SNMP Trap Receiver Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (sudo)"
    exit 1
fi

# 1. Set capability on Python interpreter to bind to port 162
echo "1. Setting CAP_NET_BIND_SERVICE capability on Python..."
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "   ERROR: python3 not found"
    exit 1
fi

# Get the real path (not symlink)
PYTHON_REAL=$(readlink -f "$PYTHON_PATH")
echo "   Python path: $PYTHON_REAL"

# Set capability
setcap 'cap_net_bind_service=+ep' "$PYTHON_REAL"
echo "   ✓ Capability set"

# Verify
if getcap "$PYTHON_REAL" | grep -q cap_net_bind_service; then
    echo "   ✓ Verified: $(getcap "$PYTHON_REAL")"
else
    echo "   WARNING: Capability may not be set correctly"
fi

# 2. Install systemd service
echo ""
echo "2. Installing systemd service..."
cp "$SERVICE_FILE" /etc/systemd/system/snmp-trap-receiver.service
echo "   ✓ Service file copied to /etc/systemd/system/"

# 3. Reload systemd
echo ""
echo "3. Reloading systemd..."
systemctl daemon-reload
echo "   ✓ Systemd reloaded"

# 4. Enable service
echo ""
echo "4. Enabling service..."
systemctl enable snmp-trap-receiver.service
echo "   ✓ Service enabled"

# 5. Open firewall port (if ufw is active)
echo ""
echo "5. Checking firewall..."
if command -v ufw &> /dev/null && ufw status | grep -q "active"; then
    echo "   UFW is active, opening UDP port 162..."
    ufw allow 162/udp
    echo "   ✓ Port 162/udp opened"
else
    echo "   UFW not active or not installed, skipping"
fi

# 6. Start service
echo ""
echo "6. Starting service..."
systemctl start snmp-trap-receiver.service
sleep 2

if systemctl is-active --quiet snmp-trap-receiver.service; then
    echo "   ✓ Service started successfully"
else
    echo "   WARNING: Service may not have started correctly"
    echo "   Check logs with: journalctl -u snmp-trap-receiver -f"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start snmp-trap-receiver"
echo "  Stop:    sudo systemctl stop snmp-trap-receiver"
echo "  Status:  sudo systemctl status snmp-trap-receiver"
echo "  Logs:    journalctl -u snmp-trap-receiver -f"
echo ""
echo "Test with:"
echo "  snmptrap -v 2c -c public localhost '' 1.3.6.1.6.3.1.1.5.3"
echo ""
