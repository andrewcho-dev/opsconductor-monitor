## Fast Network Capability Scanner

Small Flask web app for scanning a network range and tracking device capabilities
in PostgreSQL. The UI is a single HTML page (`simple_table.html`) that shows
devices, lets you trigger new scans, and delete records.

### Features

- PING reachability check
- Fast TCP port checks for:
  - SNMP port
  - SSH port
  - RDP port
- Optional hostname lookup
- Asynchronous scans (non‑blocking HTTP)
- PostgreSQL `scan_results` table with one row per IP (UPSERT on re‑scan)
- Simple JSON/HTML frontend with filtering and per‑network grouping
- Adjustable scan settings stored in `config.json`

---

## 1. Requirements

- Python 3
- PostgreSQL instance you can connect to
- `snmpget`/`snmpwalk` (net‑snmp) if you later add deeper SNMP features

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### PostgreSQL

Create a database (example):

```bash
sudo -u postgres createdb network_scan
```

Configure connection in `.env` (already used by `database.py`):

```env
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=network_scan
PG_USER=postgres
PG_PASSWORD=postgres
```

Initialize tables once:

```bash
python3 -c "from database import db; db.create_tables()"
```

This creates:

- `scan_results` – core table for device scan results
- `interface_scans` – optional interface history
- `ssh_cli_scans` – optional SSH/CLI interface data

---

## 2. Configuration (`config.json`)

Scan behavior is controlled by a simple JSON file rather than env vars.
Example (this is roughly what the app will create/use by default):

```json
{
  "ping_command": "ping",
  "ping_count": "1",
  "ping_timeout": "0.3",
  "online_status": "online",
  "offline_status": "offline",
  "snmp_version": "2c",
  "snmp_community": "public",
  "snmp_port": "161",
  "snmp_timeout": "1",
  "snmp_success_status": "YES",
  "snmp_fail_status": "NO",
  "ssh_port": "22",
  "ssh_timeout": "3",
  "ssh_username": "admin",
  "ssh_password": "admin",
  "ssh_success_status": "YES",
  "ssh_fail_status": "NO",
  "rdp_port": "3389",
  "rdp_timeout": "3",
  "rdp_success_status": "YES",
  "rdp_fail_status": "NO",
  "max_threads": "100",
  "completion_message": "Capability scan completed: {online}/{total} hosts online"
}
```

You can edit these through the **Settings** page (`/settings.html`), which
reads/writes `config.json` via the `settings_routes.py`/`config.py` helpers.

---

## 3. Running the App

From the project root:

```bash
python3 app.py
```

By default it binds to `0.0.0.0:5000` (see `.env` if you change host/port).

Open in a browser:

- On the same machine: http://localhost:5000
- From your LAN:       http://<server-ip>:5000

The main page is `simple_table.html` and will be served automatically at `/`.

---

## 4. How Scanning Works

### 4.1 Fast Network Scan (SCAN button)

1. You open the **SCAN** modal and enter a CIDR (for example `10.127.0.0/24`).
2. Frontend calls `POST /scan` with `{ "network_range": "10.127.0.0/24" }`.
3. Backend (`scan_routes.start_scan`) parses the network and starts an
   asynchronous scan in a background thread.
4. The scan:
   - Pings each host
   - Checks SNMP/SSH/RDP TCP ports with short timeouts
   - Optionally resolves hostnames
   - UPSERTs results into `scan_results` (one row per IP)
5. Frontend polls `GET /progress` every 500ms to update the progress bar.
6. When status becomes `complete`, the table auto‑reloads via `GET /data`.

Multiple scans of the same range will update existing rows instead of
creating duplicates thanks to a unique constraint on `scan_results.ip_address`
and `INSERT ... ON CONFLICT DO UPDATE` logic in the scan code.

### 4.2 Selected Device Scan

1. You select specific rows in the table and hit **SCAN**.
2. Frontend posts `ip_list` to `POST /scan_selected`.
3. Backend runs a similar async scan for just those IPs and UPSERTs their
   rows in `scan_results`.
4. Progress is again tracked via `/progress` and rendered in the same modal.

### 4.3 SNMP Scan Button

The **SNMP SCAN** button currently only shows a message in the UI that bulk
SNMP scanning is not implemented in this version. The fast capability scan
still checks whether the SNMP port is open.

---

## 5. API Endpoints

These are the main HTTP endpoints exposed by `app.py` and `scan_routes.py`:

### Core

- `GET  /`                – main HTML table (`simple_table.html`)
- `GET  /data`            – JSON list of devices (flat list of dicts)
- `GET  /progress`        – current scan progress

### Scanning

- `POST /scan`
  - Body: `{ "network_range": "10.127.0.0/24" }`
  - Response: `{ "status": "started", "total": <int>, ... }`

- `POST /scan_selected`
  - Body: `{ "ip_list": ["10.0.0.1", "10.0.0.2", ...] }`
  - Response: `{ "status": "started", "total": <int>, ... }`

- `GET  /progress`
  - Example response:
    ```json
    {
      "network_range": "10.127.0.0/24",
      "scanned": 254,
      "total": 254,
      "online": 64,
      "status": "complete"
    }
    ```

- `POST /cancel_scan`
  - Cancels a running scan (if `status == "scanning"`).

### Data management

- `POST /delete_device`
  - Body: `{ "ip_address": "10.127.0.10" }`
  - Deletes that single row from `scan_results`.

- `POST /delete_selected`
  - Body: `{ "ip_list": ["10.127.0.10", "10.127.0.11"] }`
  - Bulk delete.

- `DELETE /delete/<ip_address>`
  - URI delete variant for a single IP.

### Settings

- `GET  /settings.html`   – settings UI
- `GET  /get_settings`    – returns current `config.json` as JSON
- `POST /save_settings`   – updates `config.json`
- `POST /test_settings`   – quick connectivity checks (ping, SNMP tools, SSH, DB)

---

## 6. Code Layout

Key files only (legacy AI/optical‑monitor code has been removed):

```text
app.py              # Flask app, routes, and HTML wiring
scan_routes.py      # Async scan logic (network and selected devices)
database.py         # PostgreSQL connection + helpers
config.py           # JSON config loader/saver (config.json)
settings_routes.py  # REST API backing settings.html
simple_table.html   # Main frontend (table + scan controls)
settings.html       # Settings UI
```

The remaining `.yaml`, `.txt`, and `.json` files are either data exports or
previous analysis outputs and do not affect the running app.

---

## 7. Notes / Gotchas

- Scans use threads; `max_threads` in `config.json` controls concurrency.
- The scanner currently uses ping and simple TCP connect checks – it does not
  perform deep protocol handshakes.
- Ensure PostgreSQL is reachable from the host running `app.py`.
- SNMP tools (`snmpget`, `snmpwalk`) are only required if you later add back
  the heavier SNMP features from `server.py.backup`.
