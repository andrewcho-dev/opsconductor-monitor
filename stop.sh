#!/bin/bash
# OpsConductor Monitor - Stop Script

echo "🛑 Stopping OpsConductor Monitor..."

pkill -9 -f "python.*app.py" 2>/dev/null || true
pkill -9 -f "celery.*worker" 2>/dev/null || true
pkill -9 -f "celery.*beat" 2>/dev/null || true
lsof -ti:5000 | xargs -r kill -9 2>/dev/null || true

sleep 1
echo "✅ All processes stopped"
