# PRTG Integration Guide

This document covers the integration between OpsConductor and PRTG Network Monitor, including real-time alert webhooks, device synchronization to NetBox, and workflow automation.

## Table of Contents

1. [Overview](#overview)
2. [Configuration](#configuration)
3. [Real-Time Alerts Setup](#real-time-alerts-setup)
4. [API Endpoints](#api-endpoints)
5. [Workflow Builder Nodes](#workflow-builder-nodes)
6. [NetBox Synchronization](#netbox-synchronization)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The PRTG integration provides:

- **Real-Time Alerts** - Receive PRTG alerts instantly via webhook
- **Device Sync** - Sync PRTG devices to NetBox
- **Workflow Automation** - Use PRTG data in visual workflows
- **Alert Management** - View, acknowledge, and resolve alerts in OpsConductor

### Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│                 │ Webhook │                 │  Sync   │                 │
│  PRTG Network   │────────▶│  OpsConductor   │────────▶│     NetBox      │
│    Monitor      │         │                 │         │                 │
│                 │◀────────│                 │         │                 │
└─────────────────┘   API   └─────────────────┘         └─────────────────┘
```

---

## Configuration

### 1. OpsConductor Settings

Navigate to **System → Settings → PRTG** to configure the integration.

#### Required Settings

| Setting | Description |
|---------|-------------|
| **PRTG Server URL** | Full URL to your PRTG server (e.g., `https://prtg.example.com`) |
| **API Token** | PRTG API token (recommended) |

#### Alternative Authentication

If API tokens are not available, you can use:
- **Username** - PRTG username
- **Passhash** - User's passhash (found in PRTG Account Settings)

#### Optional Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Verify SSL** | `true` | Verify SSL certificate (disable for self-signed certs) |
| **Enabled** | `false` | Enable/disable the integration |
| **Sync Interval** | `300` | Seconds between automatic syncs |

### 2. Generate PRTG API Token

1. Log into PRTG as an administrator
2. Go to **Setup → Account Settings → API Keys**
3. Click **Create API Key**
4. Give it a descriptive name (e.g., "OpsConductor Integration")
5. Copy the generated token
6. Paste into OpsConductor PRTG settings

### 3. Test Connection

Click **Test Connection** in OpsConductor to verify:
- URL is correct
- Authentication works
- PRTG is reachable

---

## Real-Time Alerts Setup

To receive alerts from PRTG in real-time, configure PRTG to send HTTP notifications to OpsConductor.

### Step 1: Create Notification Template in PRTG

1. In PRTG, go to **Setup → Account Settings → Notification Templates**
2. Click **Add Notification Template**
3. Name it "OpsConductor Webhook"
4. Under **Notification Summarization**, select your preference
5. Click **Add Notification** and select **Execute HTTP Action**

### Step 2: Configure HTTP Action

Set the following parameters:

| Field | Value |
|-------|-------|
| **URL** | `http://your-opsconductor-server:5000/api/prtg/webhook` |
| **HTTP Method** | `POST` |
| **Content Type** | `application/x-www-form-urlencoded` |

### Step 3: Configure POST Data

Use the following POST body to send comprehensive alert data:

```
sensorid=%sensorid&deviceid=%deviceid&device=%device&sensor=%name&status=%status&statusid=%statusid&message=%message&datetime=%datetime&duration=%duration&probe=%probe&group=%group&priority=%priority&tags=%tags&host=%host&lastvalue=%lastvalue
```

#### Available PRTG Variables

| Variable | Description |
|----------|-------------|
| `%sensorid` | Sensor ID |
| `%deviceid` | Device ID |
| `%device` | Device name |
| `%name` | Sensor name |
| `%status` | Status text (Up, Down, Warning) |
| `%statusid` | Status ID number |
| `%message` | Status message |
| `%datetime` | Date/time of event |
| `%duration` | Duration of current state |
| `%probe` | Probe name |
| `%group` | Group name |
| `%priority` | Priority level |
| `%tags` | Sensor tags |
| `%host` | Device IP/hostname |
| `%lastvalue` | Last sensor value |

### Step 4: Assign Notification to Sensors

1. Go to the device, group, or sensor you want to monitor
2. Click **Settings** → **Notification Triggers**
3. Add triggers for the states you want to be notified about:
   - **State Down** → OpsConductor Webhook
   - **State Warning** → OpsConductor Webhook
   - **State Unusual** → OpsConductor Webhook
   - **State Up** (for recovery notifications)

### Step 5: Test the Webhook

1. In OpsConductor, go to **System → Settings → PRTG**
2. Note the webhook URL shown
3. In PRTG, trigger a test notification or wait for an actual alert
4. Check OpsConductor for the received alert

---

## API Endpoints

### Webhook Endpoint

```http
POST /api/prtg/webhook
```

Receives alerts from PRTG. Accepts both JSON and form-encoded data.

### Connection Status

```http
GET /api/prtg/status
```

Returns PRTG connection status and system info.

### Devices

```http
GET /api/prtg/devices
GET /api/prtg/devices?group=Network&status=up
```

Query parameters:
- `group` - Filter by group name
- `status` - Filter by status (up, down, warning, paused)
- `search` - Search by name or IP

### Sensors

```http
GET /api/prtg/sensors
GET /api/prtg/sensors?device_id=1234&status=down
```

Query parameters:
- `device_id` - Filter by device ID
- `status` - Filter by status
- `type` - Filter by sensor type

### Alerts

```http
GET /api/prtg/alerts
GET /api/prtg/alerts?status=active&severity=down
```

Query parameters:
- `status` - active, acknowledged, resolved
- `severity` - down, warning, unusual
- `device` - Filter by device name
- `sensor` - Filter by sensor name

### Acknowledge Alert

```http
POST /api/prtg/alerts/:id/acknowledge
```

```json
{
  "user": "admin",
  "notes": "Investigating the issue"
}
```

### Resolve Alert

```http
POST /api/prtg/alerts/:id/resolve
```

```json
{
  "notes": "Issue resolved - replaced faulty cable"
}
```

### NetBox Sync

```http
POST /api/prtg/sync/netbox
```

```json
{
  "dry_run": false,
  "create_missing": true,
  "update_existing": false,
  "default_site": 1,
  "default_role": 2
}
```

### Sync Preview

```http
GET /api/prtg/sync/preview
```

Returns a preview of what would be synced to NetBox.

---

## Workflow Builder Nodes

The PRTG package provides nodes for workflow automation:

### Query Nodes

| Node | Description |
|------|-------------|
| **Get PRTG Devices** | Retrieve devices with optional filtering |
| **Get PRTG Sensors** | Retrieve sensors with optional filtering |
| **Get Sensor Details** | Get detailed info for a specific sensor |
| **Get PRTG Alerts** | Get current alerts from PRTG |
| **Get PRTG Groups** | Get device groups |
| **Get Sensor History** | Get historical data for a sensor |

### Action Nodes

| Node | Description |
|------|-------------|
| **Acknowledge Alarm** | Acknowledge an alarm in PRTG |
| **Pause Object** | Pause a sensor, device, or group |
| **Resume Object** | Resume a paused object |

### Sync Nodes

| Node | Description |
|------|-------------|
| **Sync to NetBox** | Sync PRTG devices to NetBox |
| **Preview NetBox Sync** | Preview what would be synced |

### Trigger Nodes

| Node | Description |
|------|-------------|
| **PRTG Alert Trigger** | Trigger workflow when alert is received |

### Example Workflow: Auto-Acknowledge and Notify

```
[PRTG Alert Trigger] 
    → [Filter: severity = warning]
    → [Acknowledge Alarm]
    → [Send Slack Notification]
```

### Example Workflow: Device Discovery to NetBox

```
[Manual Trigger]
    → [Get PRTG Devices]
    → [Preview NetBox Sync]
    → [Sync to NetBox (dry_run: false)]
    → [Send Email Report]
```

---

## NetBox Synchronization

### Overview

The sync process:
1. Fetches all devices from PRTG
2. Compares with existing NetBox devices (by IP or name)
3. Creates new devices in NetBox for those not found
4. Optionally updates existing devices

### Sync Options

| Option | Description |
|--------|-------------|
| `dry_run` | Preview changes without making them |
| `create_missing` | Create devices that exist in PRTG but not NetBox |
| `update_existing` | Update devices that already exist in NetBox |
| `default_site` | NetBox site ID for new devices |
| `default_role` | NetBox device role ID for new devices |
| `device_ids` | Specific PRTG device IDs to sync (null = all) |

### Mapping

| PRTG Field | NetBox Field |
|------------|--------------|
| Device Name | `name` |
| Host IP | `primary_ip4` |
| Group | `comments` |
| Tags | `comments` |

### Running a Sync

#### Via UI

1. Go to **System → Settings → PRTG**
2. Click **Preview Sync** to see what would be synced
3. Use the workflow builder to create a sync workflow

#### Via API

```bash
# Preview
curl http://localhost:5000/api/prtg/sync/preview

# Execute sync
curl -X POST http://localhost:5000/api/prtg/sync/netbox \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "default_site": 1, "default_role": 2}'
```

#### Via Workflow

Create a workflow with the **Sync to NetBox** node.

---

## Troubleshooting

### Connection Issues

**Error: "PRTG URL not configured"**
- Ensure the PRTG URL is set in Settings → PRTG

**Error: "Authentication failed"**
- Verify API token or username/passhash
- Check that the user has API access in PRTG

**Error: "SSL certificate verify failed"**
- If using self-signed certificate, disable "Verify SSL" in settings

### Webhook Issues

**Alerts not being received**
1. Check PRTG notification template is configured correctly
2. Verify the webhook URL is accessible from PRTG server
3. Check OpsConductor logs for incoming requests
4. Test with: `curl -X POST http://your-server:5000/api/prtg/webhook/test`

**Alerts received but not processed**
- Check the POST data format matches expected fields
- Review OpsConductor logs for parsing errors

### Sync Issues

**Devices not appearing in NetBox**
- Ensure NetBox integration is configured
- Check that default_site and default_role are valid
- Review sync errors in the response

**Duplicate devices**
- The sync matches by IP address and device name
- Ensure consistent naming between PRTG and NetBox

### Logs

Check logs for PRTG-related issues:

```bash
# Backend logs
tail -f /var/log/opsconductor/backend.log | grep -i prtg

# Or in the UI
System → Logs → Filter by "prtg"
```

---

## Database Schema

The PRTG integration uses these tables:

### prtg_alerts

Stores alerts received via webhook:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `prtg_object_id` | VARCHAR | PRTG object ID |
| `device_id` | VARCHAR | PRTG device ID |
| `device_name` | VARCHAR | Device name |
| `sensor_id` | VARCHAR | PRTG sensor ID |
| `sensor_name` | VARCHAR | Sensor name |
| `status` | VARCHAR | active, acknowledged, resolved |
| `severity` | VARCHAR | down, warning, unusual, up |
| `message` | TEXT | Alert message |
| `host` | VARCHAR | Device IP/hostname |
| `created_at` | TIMESTAMP | When alert was received |

### prtg_devices

Cache of PRTG devices for faster lookups:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `prtg_id` | VARCHAR | PRTG device ID |
| `device_name` | VARCHAR | Device name |
| `host` | VARCHAR | IP/hostname |
| `netbox_device_id` | INTEGER | Linked NetBox device |

---

## Security Considerations

1. **API Token Security** - Store API tokens securely; they provide full API access
2. **Webhook Authentication** - Consider adding authentication to the webhook endpoint
3. **Network Access** - Ensure PRTG can reach OpsConductor webhook URL
4. **SSL/TLS** - Use HTTPS for both PRTG and OpsConductor in production
