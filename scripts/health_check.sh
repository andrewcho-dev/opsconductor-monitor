#!/bin/bash
# OpsConductor Health Check Script
# Run via cron: */5 * * * * /path/to/health_check.sh >> /var/log/opsconductor/health_check.log 2>&1

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
ALERT_FILE="/var/log/opsconductor/alerts.log"

check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        echo "[$TIMESTAMP] OK: $service is running"
        return 0
    else
        echo "[$TIMESTAMP] CRITICAL: $service is NOT running"
        echo "[$TIMESTAMP] CRITICAL: $service is NOT running" >> "$ALERT_FILE"
        return 1
    fi
}

check_url() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "[$TIMESTAMP] OK: $name responding (HTTP $response)"
        return 0
    else
        echo "[$TIMESTAMP] WARNING: $name returned HTTP $response"
        echo "[$TIMESTAMP] WARNING: $name returned HTTP $response" >> "$ALERT_FILE"
        return 1
    fi
}

check_postgres() {
    if PGPASSWORD=postgres psql -h localhost -U postgres -d network_scan -c "SELECT 1" > /dev/null 2>&1; then
        echo "[$TIMESTAMP] OK: PostgreSQL is responding"
        return 0
    else
        echo "[$TIMESTAMP] CRITICAL: PostgreSQL is NOT responding"
        echo "[$TIMESTAMP] CRITICAL: PostgreSQL is NOT responding" >> "$ALERT_FILE"
        return 1
    fi
}

check_redis() {
    if redis-cli ping > /dev/null 2>&1; then
        echo "[$TIMESTAMP] OK: Redis is responding"
        return 0
    else
        echo "[$TIMESTAMP] CRITICAL: Redis is NOT responding"
        echo "[$TIMESTAMP] CRITICAL: Redis is NOT responding" >> "$ALERT_FILE"
        return 1
    fi
}

echo "=========================================="
echo "OpsConductor Health Check - $TIMESTAMP"
echo "=========================================="

# Check services
check_service "nginx"
check_service "opsconductor-api"
check_service "postgresql"
check_service "redis"

# Check endpoints
check_url "API Health" "http://localhost:5000/api/health/status"
check_url "Nginx" "http://localhost/nginx-health"

# Check databases
check_postgres
check_redis

# Disk space check
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "[$TIMESTAMP] WARNING: Disk usage at ${DISK_USAGE}%"
    echo "[$TIMESTAMP] WARNING: Disk usage at ${DISK_USAGE}%" >> "$ALERT_FILE"
else
    echo "[$TIMESTAMP] OK: Disk usage at ${DISK_USAGE}%"
fi

# Memory check
MEM_USAGE=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "[$TIMESTAMP] WARNING: Memory usage at ${MEM_USAGE}%"
    echo "[$TIMESTAMP] WARNING: Memory usage at ${MEM_USAGE}%" >> "$ALERT_FILE"
else
    echo "[$TIMESTAMP] OK: Memory usage at ${MEM_USAGE}%"
fi

echo ""
