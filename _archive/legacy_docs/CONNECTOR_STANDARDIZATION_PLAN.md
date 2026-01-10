# Connector Standardization Implementation Plan

**Date:** January 9, 2026  
**Status:** Ready for Implementation  
**Estimated Effort:** 4-6 hours

---

## Executive Summary

This document provides a detailed implementation plan to standardize all connectors, eliminate duplicate code/polling systems, and establish a clean, consistent architecture. The goal is to have a single, well-documented polling mechanism that all connectors use uniformly.

---

## Part 1: Understanding the Current Architecture

### Three Distinct Polling Systems (Keep All Three)

After careful analysis, we have **three separate systems** that serve different purposes:

| System | Table | Beat Task | Purpose |
|--------|-------|-----------|---------|
| **Connector Polling** | `connectors` | `poll_all_connectors` (60s) | Polls external alert sources (PRTG, MCP, Eaton, etc.) for **alerts** |
| **SNMP Device Polling** | `polling_configs` | `polling.scheduler_tick` (30s) | Polls network devices for **metrics** (CPU, memory, interface stats) |
| **Job Scheduler** | `scheduler_jobs` | `opsconductor.scheduler.tick` (30s) | Runs scheduled **jobs** (discovery, reports, maintenance) |

**Decision:** These three systems have distinct purposes and should remain separate. The "duplicate beat" issue was confusion about these being different systems, not actual duplicates.

---

## Part 2: Changes to Implement

### Phase 1: Remove Dead/Duplicate Code in Base Classes

#### 1.1 Remove `_poll_loop` from `PollingConnector` Base Class

**File:** `backend/connectors/base.py`

**Why:** The `_poll_loop()` method in `PollingConnector` is never used because:
- `poll_all_connectors` task creates fresh connector instances
- It calls `connector.poll()` directly, never `connector.start()`
- The asyncio task loop is dead code

**Action:** Remove lines 276-323 (the `start()`, `stop()`, and `_poll_loop()` methods). Replace with simple stubs that log warnings if called (for safety during transition).

```python
# New simplified PollingConnector.start() and stop()
async def start(self) -> None:
    """Connector lifecycle managed by Celery poll_all_connectors task."""
    self.enabled = True
    logger.debug(f"{self.connector_type} connector enabled")

async def stop(self) -> None:
    """Connector lifecycle managed by Celery poll_all_connectors task."""
    self.enabled = False
    logger.debug(f"{self.connector_type} connector disabled")
```

#### 1.2 Remove PRTG's Custom `_poll_loop`

**File:** `backend/connectors/prtg/connector.py`

**Why:** PRTG has its own `_poll_loop()` method (lines 205-227) that duplicates what `poll_all_connectors` does.

**Action:** 
- Remove the custom `_poll_loop()` method entirely
- Update `start()` to not create asyncio task
- Remove `_polling` and `_poll_task` instance variables

---

### Phase 2: Migrate Cisco ASA from paramiko to asyncssh

#### 2.1 Analysis: paramiko vs asyncssh

| Factor | paramiko | asyncssh |
|--------|----------|----------|
| **Async Support** | ❌ Requires ThreadPoolExecutor | ✅ Native async/await |
| **Concurrency** | Thread-based (memory overhead) | Event loop (efficient) |
| **Code Complexity** | Higher (thread pool management) | Lower (clean async) |
| **Compatibility** | Excellent | Good (works with Ubiquiti) |
| **Performance** | Good with threads | Better (non-blocking I/O) |

**Decision:** Use `asyncssh` for all SSH connectors.

- Ubiquiti already uses `asyncssh` successfully
- Native async is cleaner and more efficient
- No ThreadPoolExecutor overhead
- Consistent with our async-first architecture

#### 2.2 Cisco ASA Migration Steps

**File:** `backend/connectors/cisco_asa/connector.py`

**Changes:**
1. Replace `import paramiko` with `import asyncssh`
2. Remove `_ssh_executor = ThreadPoolExecutor(max_workers=10)`
3. Convert `_get_connection_sync()` → `async def _get_connection()`
4. Convert `_run_command_sync()` → `async def _run_command()`
5. Remove `loop.run_in_executor()` wrappers
6. Update SSH connection handling to use asyncssh patterns (like Ubiquiti)

**Code Pattern (from Ubiquiti):**
```python
async with asyncssh.connect(
    ip,
    username=username,
    password=password,
    known_hosts=None,
    server_host_key_algs=['ssh-rsa'],
    connect_timeout=10
) as conn:
    result = await conn.run(command, check=True)
    return result.stdout
```

**ASA-Specific Considerations:**
- ASA uses interactive shell mode (needs `terminal pager 0`)
- May need to use `asyncssh.connect()` with `create_process()` for interactive shell
- Test with actual ASA device before finalizing

---

### Phase 3: Migrate Milestone from requests to aiohttp

#### 3.1 Analysis

| Factor | requests + ThreadPool | aiohttp |
|--------|----------------------|---------|
| **Async Support** | ❌ Requires ThreadPoolExecutor | ✅ Native async |
| **NTLM Auth** | ✅ requests-ntlm | ✅ aiohttp-negotiate or httpx-ntlm |
| **Complexity** | Higher | Lower |

**Decision:** Migrate to `aiohttp` with `aiohttp-negotiate` for NTLM.

#### 3.2 Milestone Migration Steps

**File:** `backend/connectors/milestone/connector.py`

**Changes:**
1. Replace `import requests` and `from requests_ntlm import HttpNtlmAuth`
2. Add `import aiohttp` and NTLM handling
3. Remove `_executor = ThreadPoolExecutor(max_workers=4)`
4. Convert all sync methods to async:
   - `_authenticate_sync()` → `async def _authenticate()`
   - `_poll_sync()` → Merge into `async def poll()`
   - `_get_cameras_sync()` → `async def _get_cameras()`
   - `_get_hardware_sync()` → `async def _get_hardware()`
   - etc.
5. Remove `loop.run_in_executor()` wrappers

**NTLM Handling Option:**
```python
# Option 1: Use httpx with httpx-ntlm (recommended - simpler)
import httpx
from httpx_ntlm import HttpNtlmAuth

async with httpx.AsyncClient(auth=HttpNtlmAuth(username, password)) as client:
    response = await client.get(url)

# Option 2: Manual token acquisition then use aiohttp with Bearer token
# (Already partially implemented - just make fully async)
```

---

### Phase 4: Standardize Method Signatures

#### 4.1 Standard `_create_alert` Signature

All connectors should use this consistent signature:

```python
def _create_alert(
    self, 
    target: Dict, 
    alert_type: str, 
    metrics: Dict
) -> Optional[NormalizedAlert]:
    """Create a normalized alert.
    
    Args:
        target: Device target dict with 'ip', 'name' keys
        alert_type: Type of alert (e.g., 'device_offline', 'high_cpu')
        metrics: Additional metrics/data for the alert
        
    Returns:
        NormalizedAlert or None if event type is disabled
    """
    raw_data = {
        "device_ip": target.get("ip"),
        "device_name": target.get("name", target.get("ip", "")),
        "alert_type": alert_type,
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return self.normalizer.normalize(raw_data)
```

**Connectors to Update:**
- **Ubiquiti**: Change `_create_alert(ip, name, alert_type, metrics)` → use target dict
- **Milestone**: Consolidate `_create_alert`, `_create_alert_with_ip`, `_create_event_alert` into one

#### 4.2 Add Missing `_process_alerts` to Cisco ASA

**File:** `backend/connectors/cisco_asa/connector.py`

**Add:**
```python
async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
    """Process alerts through AlertManager."""
    from backend.core.alert_manager import get_alert_manager
    
    alert_manager = get_alert_manager()
    for normalized in alerts:
        if normalized is None:
            continue
        try:
            await alert_manager.process_alert(normalized)
        except Exception as e:
            logger.warning(f"Failed to process Cisco ASA alert: {e}")
```

---

### Phase 5: Clean Up Celery Beat Configuration

#### 5.1 Consolidate Beat Schedule

**File:** `celery_app.py`

Keep the existing beat_schedule (it's correct):
```python
beat_schedule={
    "opsconductor-scheduler-tick": {
        "task": "opsconductor.scheduler.tick",
        "schedule": 30.0,
    },
    "opsconductor-alerts-evaluate": {
        "task": "opsconductor.alerts.evaluate",
        "schedule": 60.0,
    },
    "opsconductor-polling-scheduler": {
        "task": "polling.scheduler_tick",
        "schedule": 30.0,
    },
    "opsconductor-connector-polling": {
        "task": "poll_all_connectors",
        "schedule": 60.0,
    },
}
```

#### 5.2 Simplify `celery_beat_schedule.py`

**File:** `backend/celery_beat_schedule.py`

**Option A (Recommended):** Delete this file entirely and move `reset-daily-counters` into `celery_app.py`.

**Option B:** Keep but add clear documentation:
```python
"""
Celery Beat Schedule - ADDITIONAL schedules only.

The main beat schedule is defined in celery_app.py.
This file ONLY adds supplemental schedules.
DO NOT duplicate entries from celery_app.py here.
"""
```

---

### Phase 6: Session Management Standardization

#### 6.1 Standard Pattern for HTTP Connectors

All HTTP-based connectors should use per-target session caching:

```python
class HttpPollingConnector(PollingConnector):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
    
    async def _get_session(self, target: Dict) -> aiohttp.ClientSession:
        """Get or create session for target."""
        key = target.get("ip") or target.get("url", "default")
        if key not in self._sessions or self._sessions[key].closed:
            self._sessions[key] = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            )
        return self._sessions[key]
    
    async def stop(self) -> None:
        """Close all sessions on stop."""
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()
        await super().stop()
```

**Apply to:** Axis, Cradlepoint (already have this), PRTG, MCP, Milestone (after migration)

---

## Part 3: Implementation Order

Execute in this order to minimize risk:

### Step 1: Base Class Cleanup (Low Risk)
1. Remove `_poll_loop` from `PollingConnector` base class
2. Remove PRTG's custom `_poll_loop`
3. Test: Verify connector polling still works via Celery

### Step 2: Cisco ASA Migration (Medium Risk)
1. Create backup of current `cisco_asa/connector.py`
2. Rewrite using asyncssh
3. Test with actual ASA device
4. Remove paramiko import and ThreadPoolExecutor

### Step 3: Milestone Migration (Medium Risk)
1. Create backup of current `milestone/connector.py`
2. Rewrite using aiohttp/httpx with NTLM
3. Test with actual Milestone server
4. Remove requests import and ThreadPoolExecutor

### Step 4: Method Standardization (Low Risk)
1. Update Ubiquiti `_create_alert` signature
2. Consolidate Milestone alert creation methods
3. Add `_process_alerts` to Cisco ASA

### Step 5: Configuration Cleanup (Low Risk)
1. Move `reset-daily-counters` to `celery_app.py`
2. Delete or simplify `celery_beat_schedule.py`
3. Add documentation comments

### Step 6: Testing & Verification
1. Restart all services
2. Verify each connector can poll successfully
3. Check Celery flower for task execution
4. Monitor logs for errors

---

## Part 4: Files to Modify

| File | Action | Risk |
|------|--------|------|
| `backend/connectors/base.py` | Remove `_poll_loop`, simplify `start()`/`stop()` | Low |
| `backend/connectors/prtg/connector.py` | Remove custom `_poll_loop` | Low |
| `backend/connectors/cisco_asa/connector.py` | Full rewrite: paramiko → asyncssh | Medium |
| `backend/connectors/milestone/connector.py` | Full rewrite: requests → aiohttp | Medium |
| `backend/connectors/ubiquiti/connector.py` | Update `_create_alert` signature | Low |
| `celery_app.py` | Add `reset-daily-counters` task | Low |
| `backend/celery_beat_schedule.py` | Delete or simplify | Low |

---

## Part 5: Dependencies

### Current
- `paramiko` - SSH (Cisco ASA) - **TO BE REMOVED**
- `requests` - HTTP (Milestone) - **TO BE REMOVED**
- `requests-ntlm` - NTLM auth - **TO BE REMOVED**

### After Migration
- `asyncssh` - SSH (Ubiquiti, Cisco ASA) - **KEEP**
- `aiohttp` - HTTP (all HTTP connectors) - **KEEP**
- `httpx` + `httpx-ntlm` - NTLM auth for Milestone - **ADD**

### Update requirements.txt
```diff
- paramiko>=3.0.0
- requests>=2.28.0
- requests-ntlm>=1.2.0
+ httpx>=0.24.0
+ httpx-ntlm>=1.0.0
```

---

## Part 6: Verification Checklist

After implementation, verify:

- [ ] All connectors poll successfully via Celery `poll_all_connectors`
- [ ] No asyncio task loops running in connectors (check with `asyncio.all_tasks()`)
- [ ] No ThreadPoolExecutor usage in connectors
- [ ] Celery flower shows single beat process
- [ ] Each connector's `test_connection` works
- [ ] Alerts flow correctly from connectors → AlertManager → Database
- [ ] No duplicate alerts being created
- [ ] Logs show clean polling cycles without errors

---

## Summary

This plan eliminates:
- ❌ Dead `_poll_loop` code in base class
- ❌ PRTG's duplicate poll loop
- ❌ ThreadPoolExecutor usage in connectors (Milestone, Cisco ASA)
- ❌ Inconsistent method signatures
- ❌ Scattered beat schedule definitions

And establishes:
- ✅ Single polling mechanism via Celery `poll_all_connectors`
- ✅ Consistent async-first architecture (aiohttp, asyncssh)
- ✅ Standardized method signatures across all connectors
- ✅ Clean, documented Celery beat configuration
- ✅ Uniform session management patterns

---

# PART 7: FRONTEND STANDARDIZATION

## 7.1 Current Frontend Inconsistencies

### Two Separate Configuration Systems

| System | Location | Used By | API Pattern |
|--------|----------|---------|-------------|
| **ConfigModal** | `components/connectors/ConfigModal.jsx` | ConnectorsPage | `/api/v1/connectors/{id}` |
| **Settings Pages** | `pages/system/settings/*.jsx` | System Settings sidebar | `/integrations/v1/{connector}/settings` |

**Problem:** Same connectors configured in two different places with different APIs.

### Duplicated Code in ConfigModal.jsx

The following code is **nearly identical** across 5+ connector forms:

1. **Bulk Import Logic** (~60 lines each)
   - `handleBulkImport()` function
   - CSV/tab parsing
   - IP validation
   - Duplicate detection
   - Error handling

2. **Device List Management** (~40 lines each)
   - `addDevice()`/`addTarget()`/`addRouter()`/`addCamera()`
   - `removeDevice()`/`removeTarget()`
   - `clearAllDevices()`
   - Device list rendering

3. **State Management** (~10 lines each)
   - `useState` for newDevice/newTarget
   - `useState` for bulkImportText
   - `useState` for showBulkImport
   - `useState` for importError

### Connectors Missing Custom Forms

| Connector | ConfigModal Form | Settings Page | Status |
|-----------|------------------|---------------|--------|
| PRTG | ❌ Generic | ✅ PRTGSettings.jsx | **Inconsistent** |
| MCP | ❌ Generic | ✅ MCPSettings.jsx | **Inconsistent** |
| Axis | ✅ AxisConfigForm | ❌ None | OK |
| Milestone | ✅ MilestoneConfigForm | ❌ None | OK |
| Cradlepoint | ✅ CradlepointConfigForm | ❌ None | OK |
| Cisco ASA | ✅ CiscoASAConfigForm | ❌ None | OK |
| Eaton REST | ✅ EatonRESTConfigForm | ❌ None | OK |
| Eaton SNMP | ❌ Generic | ❌ None | **Missing** |
| Siklu | ❌ Generic | ❌ None | **Missing** |
| Ubiquiti | ✅ UbiquitiConfigForm | ✅ UbiquitiSettings.jsx | **Duplicate** |
| SNMP Trap | ✅ SNMPTrapConfigForm | ❌ None | OK |

---

## 7.2 Frontend Standardization Plan

### Decision: Single Configuration Location

**Recommendation:** Use **ConfigModal only** for connector configuration.

**Rationale:**
- Connectors are already managed via the Connectors page
- ConfigModal is embedded in the workflow (click connector → configure)
- Settings pages are for global system settings, not per-connector config
- Eliminates duplicate code and APIs

### Phase F1: Create Reusable Components

#### F1.1 Create `DeviceTargetManager` Component

Extract common device list management into a reusable component:

**File:** `frontend/src/components/connectors/DeviceTargetManager.jsx`

```jsx
/**
 * Reusable component for managing device targets with bulk import.
 * Used by: Cradlepoint, Axis, Eaton, Ubiquiti, Cisco ASA, Siklu
 */
export default function DeviceTargetManager({
  targets,              // Array of {ip, name, username?, password?}
  onTargetsChange,      // Callback when targets change
  defaultUsername,      // Default username for new devices
  defaultPassword,      // Default password for new devices
  deviceLabel = "Device", // "Router", "Camera", "UPS", etc.
  showCredentials = true, // Show username/password fields
  bulkImportFormat = "IP,Name,Username,Password", // Help text
}) {
  // All the shared logic here:
  // - useState for newDevice, bulkImportText, showBulkImport, importError
  // - handleBulkImport() with validation
  // - addDevice(), removeDevice(), clearAllDevices()
  // - Device list rendering with Remove buttons
  // - Add device form row
  // - Bulk import textarea and button
}
```

#### F1.2 Create `ThresholdEditor` Component

Extract threshold configuration:

**File:** `frontend/src/components/connectors/ThresholdEditor.jsx`

```jsx
/**
 * Reusable threshold configuration editor.
 */
export default function ThresholdEditor({
  thresholds,           // Object with threshold values
  onThresholdsChange,   // Callback when thresholds change
  fields,               // Array of {key, label, unit, min, max, default}
  columns = 2,          // Grid columns
}) {
  // Renders grid of threshold inputs
}
```

#### F1.3 Create `MonitoringOptions` Component

Extract monitoring checkboxes:

**File:** `frontend/src/components/connectors/MonitoringOptions.jsx`

```jsx
/**
 * Reusable monitoring options checkboxes.
 */
export default function MonitoringOptions({
  config,
  onConfigChange,
  options,  // Array of {key, label, defaultValue}
  columns = 2,
}) {
  // Renders grid of checkboxes
}
```

### Phase F2: Refactor ConfigModal Forms

#### F2.1 Simplify Each Connector Form

Each connector form becomes much simpler:

```jsx
// Example: CradlepointConfigForm after refactoring
function CradlepointConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      {/* Info banner */}
      <ConnectorInfoBanner 
        title="Cradlepoint IBR900 Direct Connection"
        description="Connect directly to Cradlepoint routers via the local NCOS API."
        color="blue"
      />

      {/* Default credentials */}
      <CredentialsSection
        username={config.default_username}
        password={config.default_password}
        onUsernameChange={(v) => setConfig({...config, default_username: v})}
        onPasswordChange={(v) => setConfig({...config, default_password: v})}
        defaultUsername="admin"
      />

      {/* Poll interval */}
      <PollIntervalInput
        value={config.poll_interval}
        onChange={(v) => setConfig({...config, poll_interval: v})}
        min={30}
        default={60}
      />

      {/* Signal thresholds */}
      <ThresholdEditor
        thresholds={config.thresholds}
        onThresholdsChange={(t) => setConfig({...config, thresholds: t})}
        fields={[
          {key: 'rsrp_warning', label: 'RSRP Warning', unit: 'dBm', default: -100},
          {key: 'rsrp_critical', label: 'RSRP Critical', unit: 'dBm', default: -110},
          {key: 'sinr_warning', label: 'SINR Warning', unit: 'dB', default: 5},
          {key: 'sinr_critical', label: 'SINR Critical', unit: 'dB', default: 0},
        ]}
      />

      {/* Device list with bulk import */}
      <DeviceTargetManager
        targets={config.targets}
        onTargetsChange={(t) => setConfig({...config, targets: t})}
        defaultUsername={config.default_username || 'admin'}
        defaultPassword={config.default_password}
        deviceLabel="Router"
        showCredentials={true}
        bulkImportFormat="IP,Name,Password"
      />

      {/* Monitoring options */}
      <MonitoringOptions
        config={config}
        onConfigChange={setConfig}
        options={[
          {key: 'monitor_signal', label: 'Cellular Signal', defaultValue: true},
          {key: 'monitor_connection', label: 'Connection State', defaultValue: true},
          {key: 'monitor_temperature', label: 'Temperature', defaultValue: true},
          {key: 'monitor_gps', label: 'GPS Status', defaultValue: true},
          {key: 'monitor_ethernet', label: 'Ethernet Ports', defaultValue: false},
        ]}
      />
    </div>
  );
}
```

### Phase F3: Remove/Deprecate Settings Pages

#### F3.1 Files to Remove

| File | Action | Replacement |
|------|--------|-------------|
| `UbiquitiSettings.jsx` | **DELETE** | UbiquitiConfigForm in ConfigModal |
| `PRTGSettings.jsx` | **KEEP** (has unique sync features) | Or move to ConfigModal |
| `MCPSettings.jsx` | **KEEP** (has unique sync features) | Or move to ConfigModal |

**Note:** PRTG and MCP settings pages have device sync features that go beyond just configuration. Decision needed:
- Option A: Keep as full pages for advanced features
- Option B: Move sync features to a separate "Sync" tab/modal

#### F3.2 Update Sidebar Navigation

**File:** `frontend/src/components/layout/ModuleSidebar.jsx`

Remove Ubiquiti from settings sidebar (it's accessed via Connectors page).

### Phase F4: Add Missing Connector Forms

#### F4.1 Create SikluConfigForm

```jsx
function SikluConfigForm({ config, setConfig }) {
  return (
    <div className="space-y-4">
      <ConnectorInfoBanner 
        title="Siklu EtherHaul Radios"
        description="Poll Siklu radios via SNMP for link status and signal metrics."
        color="blue"
      />

      <div>
        <label>SNMP Community</label>
        <input value={config.snmp_community} onChange={...} />
      </div>

      <PollIntervalInput value={config.poll_interval} onChange={...} />

      <ThresholdEditor
        thresholds={config.thresholds}
        fields={[
          {key: 'rsl_warning', label: 'RSL Warning', unit: 'dBm', default: -55},
          {key: 'rsl_critical', label: 'RSL Critical', unit: 'dBm', default: -60},
        ]}
      />

      <DeviceTargetManager
        targets={config.targets}
        onTargetsChange={...}
        deviceLabel="Radio"
        showCredentials={false}  // SNMP uses community string
        bulkImportFormat="IP,Name,PeerIP"
      />
    </div>
  );
}
```

#### F4.2 Create EatonSNMPConfigForm

```jsx
function EatonSNMPConfigForm({ config, setConfig }) {
  // Similar structure for Eaton SNMP polling
}
```

---

## 7.3 Frontend Files to Modify

| File | Action | Effort |
|------|--------|--------|
| `components/connectors/DeviceTargetManager.jsx` | **CREATE** | Medium |
| `components/connectors/ThresholdEditor.jsx` | **CREATE** | Low |
| `components/connectors/MonitoringOptions.jsx` | **CREATE** | Low |
| `components/connectors/ConnectorInfoBanner.jsx` | **CREATE** | Low |
| `components/connectors/CredentialsSection.jsx` | **CREATE** | Low |
| `components/connectors/PollIntervalInput.jsx` | **CREATE** | Low |
| `components/connectors/ConfigModal.jsx` | **REFACTOR** - Use new components | Medium |
| `pages/system/settings/UbiquitiSettings.jsx` | **DELETE** | Low |
| `components/layout/ModuleSidebar.jsx` | **UPDATE** - Remove Ubiquiti link | Low |

---

## 7.4 Frontend Implementation Order

1. **Create reusable components** (DeviceTargetManager, ThresholdEditor, etc.)
2. **Refactor one connector form** as proof of concept (e.g., Cradlepoint)
3. **Refactor remaining connector forms** using the new components
4. **Add missing forms** (Siklu, Eaton SNMP)
5. **Delete UbiquitiSettings.jsx** and update sidebar
6. **Test all connectors** via ConfigModal

---

## Summary: Full Standardization

### Backend Eliminates:
- ❌ Dead `_poll_loop` code
- ❌ Duplicate poll loops (PRTG)
- ❌ ThreadPoolExecutor (Milestone, Cisco ASA)
- ❌ Inconsistent method signatures
- ❌ Scattered beat schedules

### Frontend Eliminates:
- ❌ Duplicate bulk import code (5+ copies → 1 component)
- ❌ Duplicate device list management (5+ copies → 1 component)
- ❌ Two configuration locations (ConfigModal + Settings pages)
- ❌ Missing connector forms (Siklu, Eaton SNMP)
- ❌ Inconsistent UI patterns

### Establishes:
- ✅ Single polling mechanism (Celery)
- ✅ Consistent async architecture (aiohttp, asyncssh)
- ✅ Standardized backend method signatures
- ✅ Reusable frontend components
- ✅ Single configuration location (ConfigModal)
- ✅ Consistent UI patterns across all connectors

---

# PART 8: ALERT MAPPING STANDARDIZATION

## 8.1 Current Alert Mapping Architecture

### Database Tables (from migration 021)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `severity_mappings` | Map source values → severity | connector_type, source_value, source_field, target_severity |
| `category_mappings` | Map source values → category | connector_type, source_value, source_field, target_category |
| `priority_rules` | Calculate priority (ITIL) | connector_type, category, severity, impact, urgency, priority |
| `alert_type_templates` | Generate alert type strings | connector_type, pattern, template |
| `deduplication_rules` | Fingerprint rules | connector_type, fingerprint_fields, dedup_window_minutes |

### Frontend Alert Mapping Page

**File:** `frontend/src/pages/ColumnMappingPage.jsx` (renamed to NormalizationRulesPage)

- Single page for all connectors
- Dropdown to select connector type
- Two-column layout: Source Values → OpsConductor Values
- CRUD for severity and category mappings
- **Missing:** Priority rules UI, Alert type templates UI, Deduplication rules UI

---

## 8.2 Alert Mapping Inconsistencies Found

### 8.2.1 Backend Normalizer Inconsistencies

| Connector | Normalizer Class | Extends Base? | Check Method | Default Category |
|-----------|-----------------|---------------|--------------|------------------|
| **PRTG** | `PRTGDatabaseNormalizer` | ❌ No | N/A (always processes) | N/A |
| **Axis** | `AxisNormalizer` | ❌ No | `is_event_enabled()` | `VIDEO` |
| **Milestone** | `MilestoneNormalizer` | ❌ No | `is_event_enabled()` | `VIDEO` |
| **MCP** | `MCPNormalizer` | ❌ No | `is_event_enabled()` | `NETWORK` |
| **Cradlepoint** | `CradlepointNormalizer` | ❌ No | `is_event_enabled()` | `WIRELESS` |
| **Siklu** | `SikluNormalizer` | ❌ No | `is_alert_enabled()` | `WIRELESS` |
| **Ubiquiti** | `UbiquitiNormalizer` | ❌ No | `is_event_enabled()` | `NETWORK` |
| **Cisco ASA** | `CiscoASANormalizer` | ✅ Yes (BaseNormalizer) | `is_event_enabled()` | `NETWORK` |
| **Eaton** | `EatonNormalizer` | ❌ No | `is_event_enabled()` | `POWER` |

**Issues:**
1. **Method naming inconsistency:** `is_event_enabled()` vs `is_alert_enabled()` (Siklu)
2. **Only Cisco ASA extends BaseNormalizer** - others are standalone
3. **PRTG has no enable check** - always processes events
4. **Hardcoded fallback values vary** by connector

### 8.2.2 Database Seed Data Gaps

**Migration 021 seeds data for:** PRTG, MCP only

**Missing seed data for:**
- Axis (video cameras)
- Milestone (VMS)
- Cradlepoint (cellular routers)
- Siklu (wireless radios)
- Ubiquiti (wireless APs)
- Cisco ASA (firewalls)
- Eaton (UPS)
- SNMP Traps (generic)

**Impact:** Without seed data, these connectors use hardcoded fallbacks, defeating the purpose of database-driven mappings.

### 8.2.3 Frontend Connector List Mismatch

**ColumnMappingPage.jsx connectors list:**
```javascript
const connectors = [
  { value: 'prtg', label: 'PRTG' },
  { value: 'mcp', label: 'MCP' },
  { value: 'snmp_trap', label: 'SNMP Traps' },
  { value: 'snmp_poll', label: 'SNMP Polling' },
  { value: 'eaton', label: 'Eaton UPS (SNMP)' },
  { value: 'eaton_rest', label: 'Eaton UPS (REST)' },
  { value: 'axis', label: 'Axis Cameras' },
  { value: 'milestone', label: 'Milestone VMS' },
  { value: 'cradlepoint', label: 'Cradlepoint' },
  { value: 'ubiquiti', label: 'Ubiquiti' },
  { value: 'cisco_asa', label: 'Cisco ASA' },
];
```

**Backend registry connector types:**
- `prtg`, `mcp`, `axis`, `milestone`, `cradlepoint`, `siklu`, `ubiquiti`, `cisco_asa`, `eaton`, `eaton_rest`, `snmp_trap`

**Mismatch:** Siklu is in backend but **NOT in frontend dropdown**!

### 8.2.4 Raw Data Field Naming Inconsistencies

| Connector | Event Type Field | IP Field | Name Field |
|-----------|-----------------|----------|------------|
| PRTG | `status` / `status_text` | `device_ip` | `device_name` |
| Axis | `event_type` | `device_ip` | `device_name` |
| Cradlepoint | `alert_type` | `device_ip` | `device_name` |
| Siklu | `alert_type` | `device_ip` | `device_name` |
| Ubiquiti | `alert_type` | `device_ip` | `device_name` |
| Cisco ASA | `event_type` | `device_ip` | `device_name` |
| MCP | `alarm_type` / `severity` | varies | varies |

**Issues:**
- `event_type` vs `alert_type` vs `alarm_type` - inconsistent naming
- PRTG uses `status` / `status_text` differently

### 8.2.5 Clear Event Detection Inconsistencies

| Connector | Clear Detection Method |
|-----------|----------------------|
| **PRTG** | Database mapping → `clear` severity |
| **Axis** | Suffix check: `_restored`, `_up`, `_online`, `_ok`, `_normal`, `_cleared` |
| **Cradlepoint** | Hardcoded set: `CLEAR_EVENTS = {...}` |
| **Siklu** | Hardcoded in `ALERT_TYPE_DEFAULTS` dict |
| **Ubiquiti** | Severity == CLEAR OR hardcoded list |
| **Cisco ASA** | No `is_clear` field set |

**Issues:**
- No standard approach to clear event detection
- Some use database, some use hardcoded sets, some use suffix matching

---

## 8.3 Alert Mapping Standardization Plan

### Phase M1: Standardize Normalizer Base Class

**Create standardized methods in `BaseNormalizer`:**

```python
class BaseNormalizer:
    """Standard normalizer interface - all connectors must implement."""
    
    connector_type: str  # e.g., "axis", "cradlepoint"
    
    def __init__(self):
        self._severity_cache: Dict[str, Dict] = {}
        self._category_cache: Dict[str, Dict] = {}
        self._cache_loaded = False
    
    def _load_mappings(self) -> None:
        """Load severity and category mappings from database."""
        if self._cache_loaded:
            return
        # Standard implementation for all connectors
        
    def is_event_enabled(self, event_type: str) -> bool:
        """Check if event type is enabled in mappings."""
        # Standard implementation
        
    def _get_severity(self, event_type: str) -> Severity:
        """Get severity from database mapping."""
        # Standard implementation with fallback
        
    def _get_category(self, event_type: str) -> Category:
        """Get category from database mapping."""
        # Standard implementation with fallback
    
    def is_clear_event(self, event_type: str, raw_data: Dict) -> bool:
        """Determine if this is a clear event.
        
        Standard logic:
        1. Check if severity mapping returns 'clear'
        2. Check if event_type ends with clear suffixes
        """
        severity = self._get_severity(event_type)
        if severity == Severity.CLEAR:
            return True
        
        clear_suffixes = ('_restored', '_up', '_online', '_ok', '_normal', '_cleared', '_clear')
        return event_type.lower().endswith(clear_suffixes)
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Transform raw data to NormalizedAlert. Must be implemented."""
        pass
```

### Phase M2: Refactor All Normalizers to Use Base Class

**Update each normalizer to:**
1. Extend `BaseNormalizer`
2. Use inherited `_load_mappings()`, `is_event_enabled()`, `_get_severity()`, `_get_category()`
3. Use inherited `is_clear_event()` instead of custom logic
4. Remove duplicate code

**Example refactored normalizer:**
```python
class AxisNormalizer(BaseNormalizer):
    connector_type = "axis"
    default_category = Category.VIDEO
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        event_type = raw_data.get("event_type", "unknown").lower()
        
        # Standard check from base class
        if not self.is_event_enabled(event_type):
            return None
        
        # Standard severity/category from base class
        severity = self._get_severity(event_type)
        category = self._get_category(event_type)
        
        # Standard clear detection from base class
        is_clear = self.is_clear_event(event_type, raw_data)
        
        # Connector-specific logic...
```

### Phase M3: Add Missing Database Seed Data

**Create migration 025_seed_all_connectors.sql:**

```sql
-- Axis Camera mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('axis', 'video_loss', 'critical', 'Camera video loss'),
('axis', 'video_restored', 'clear', 'Camera video restored'),
('axis', 'motion', 'info', 'Motion detected'),
('axis', 'tampering', 'major', 'Camera tampering detected'),
('axis', 'storage_full', 'warning', 'Storage capacity full'),
('axis', 'disk_error', 'critical', 'Storage disk error'),
('axis', 'high_temperature', 'warning', 'Camera temperature high'),
('axis', 'recording_error', 'major', 'Recording failure')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('axis', 'video_loss', 'video', 'Video events'),
('axis', 'motion', 'video', 'Motion events'),
('axis', 'storage_full', 'storage', 'Storage events'),
('axis', 'high_temperature', 'environment', 'Environment events')
ON CONFLICT DO NOTHING;

-- Cradlepoint mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('cradlepoint', 'signal_critical', 'critical', 'Cellular signal critical'),
('cradlepoint', 'signal_low', 'warning', 'Cellular signal low'),
('cradlepoint', 'signal_normal', 'clear', 'Cellular signal normal'),
('cradlepoint', 'connection_lost', 'critical', 'Cellular connection lost'),
('cradlepoint', 'device_offline', 'critical', 'Router offline'),
('cradlepoint', 'device_online', 'clear', 'Router online'),
('cradlepoint', 'wan_failover', 'warning', 'WAN failover active'),
('cradlepoint', 'temperature_high', 'warning', 'Temperature high')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('cradlepoint', 'signal_critical', 'wireless', 'Wireless events'),
('cradlepoint', 'device_offline', 'network', 'Network events'),
('cradlepoint', 'temperature_high', 'environment', 'Environment events')
ON CONFLICT DO NOTHING;

-- Siklu mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('siklu', 'link_down', 'critical', 'Radio link down'),
('siklu', 'link_up', 'clear', 'Radio link up'),
('siklu', 'rsl_low', 'warning', 'RSL below threshold'),
('siklu', 'rsl_critical', 'critical', 'RSL critically low'),
('siklu', 'device_offline', 'critical', 'Radio offline'),
('siklu', 'device_online', 'clear', 'Radio online'),
('siklu', 'high_temperature', 'warning', 'Radio temperature high')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('siklu', 'link_down', 'wireless', 'Wireless events'),
('siklu', 'rsl_low', 'wireless', 'Signal events'),
('siklu', 'high_temperature', 'environment', 'Environment events')
ON CONFLICT DO NOTHING;

-- Ubiquiti mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('ubiquiti', 'device_offline', 'critical', 'AP offline'),
('ubiquiti', 'device_online', 'clear', 'AP online'),
('ubiquiti', 'high_cpu', 'warning', 'CPU utilization high'),
('ubiquiti', 'high_memory', 'warning', 'Memory utilization high'),
('ubiquiti', 'signal_degraded', 'warning', 'Signal strength degraded')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('ubiquiti', 'device_offline', 'wireless', 'AP events'),
('ubiquiti', 'high_cpu', 'compute', 'Resource events'),
('ubiquiti', 'signal_degraded', 'wireless', 'Signal events')
ON CONFLICT DO NOTHING;

-- Cisco ASA mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('cisco_asa', 'vpn_tunnel_down', 'critical', 'VPN tunnel down'),
('cisco_asa', 'vpn_tunnel_up', 'clear', 'VPN tunnel established'),
('cisco_asa', 'high_cpu', 'warning', 'CPU utilization high'),
('cisco_asa', 'high_memory', 'warning', 'Memory utilization high'),
('cisco_asa', 'interface_down', 'critical', 'Interface down'),
('cisco_asa', 'interface_up', 'clear', 'Interface up'),
('cisco_asa', 'failover_active', 'warning', 'Failover to standby')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('cisco_asa', 'vpn_tunnel_down', 'security', 'VPN events'),
('cisco_asa', 'interface_down', 'network', 'Interface events'),
('cisco_asa', 'high_cpu', 'compute', 'Resource events')
ON CONFLICT DO NOTHING;

-- Eaton UPS mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('eaton', 'on_battery', 'critical', 'UPS on battery'),
('eaton', 'on_utility', 'clear', 'UPS on utility power'),
('eaton', 'low_battery', 'critical', 'Battery low'),
('eaton', 'battery_fault', 'critical', 'Battery fault detected'),
('eaton', 'overload', 'critical', 'UPS overload'),
('eaton', 'high_temperature', 'warning', 'UPS temperature high')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('eaton', 'on_battery', 'power', 'Power events'),
('eaton', 'low_battery', 'power', 'Battery events'),
('eaton', 'high_temperature', 'environment', 'Environment events')
ON CONFLICT DO NOTHING;

-- Milestone VMS mappings
INSERT INTO severity_mappings (connector_type, source_value, target_severity, description) VALUES
('milestone', 'camera_offline', 'critical', 'Camera offline'),
('milestone', 'camera_online', 'clear', 'Camera online'),
('milestone', 'recording_stopped', 'critical', 'Recording stopped'),
('milestone', 'recording_started', 'clear', 'Recording started'),
('milestone', 'storage_warning', 'warning', 'Storage space low'),
('milestone', 'storage_critical', 'critical', 'Storage space critical'),
('milestone', 'server_down', 'critical', 'Server offline')
ON CONFLICT DO NOTHING;

INSERT INTO category_mappings (connector_type, source_value, target_category, description) VALUES
('milestone', 'camera_offline', 'video', 'Camera events'),
('milestone', 'recording_stopped', 'video', 'Recording events'),
('milestone', 'storage_warning', 'storage', 'Storage events'),
('milestone', 'server_down', 'compute', 'Server events')
ON CONFLICT DO NOTHING;
```

### Phase M4: Fix Frontend Connector List

**Update `ColumnMappingPage.jsx`:**

Add missing Siklu connector to dropdown:
```javascript
const connectors = [
  { value: 'prtg', label: 'PRTG' },
  { value: 'mcp', label: 'MCP (Ciena)' },
  { value: 'snmp_trap', label: 'SNMP Traps' },
  { value: 'axis', label: 'Axis Cameras' },
  { value: 'milestone', label: 'Milestone VMS' },
  { value: 'cradlepoint', label: 'Cradlepoint' },
  { value: 'siklu', label: 'Siklu Radios' },  // ADD THIS
  { value: 'ubiquiti', label: 'Ubiquiti' },
  { value: 'cisco_asa', label: 'Cisco ASA' },
  { value: 'eaton', label: 'Eaton UPS (SNMP)' },
  { value: 'eaton_rest', label: 'Eaton UPS (REST)' },
];
```

### Phase M5: Standardize Raw Data Field Names

**Standard field naming convention:**

| Field | Purpose | Standard Name |
|-------|---------|---------------|
| Event type | Type of alert/event | `alert_type` |
| Device IP | IP address | `device_ip` |
| Device name | Friendly name | `device_name` |
| Timestamp | When event occurred | `timestamp` |
| Metrics | Additional data | `metrics` |

**Update connectors to use standard names** in their `normalize()` input expectations.

---

## 8.4 Alert Mapping Files to Modify

| File | Action | Effort |
|------|--------|--------|
| `backend/connectors/base.py` | Add standard mapping methods to BaseNormalizer | Medium |
| `backend/connectors/*/normalizer.py` | Refactor to extend BaseNormalizer | Medium (per connector) |
| `backend/migrations/025_seed_all_connectors.sql` | **CREATE** - Seed data for all connectors | Low |
| `frontend/src/pages/ColumnMappingPage.jsx` | Add Siklu to dropdown | Low |

---

## 8.5 Alert Mapping Implementation Order

1. **Update BaseNormalizer** with standard mapping methods
2. **Refactor PRTG normalizer** as the template (it has most complexity)
3. **Refactor remaining normalizers** one by one
4. **Create seed migration** with default mappings for all connectors
5. **Fix frontend dropdown** - add Siklu
6. **Test each connector** - verify mappings work from UI

---

## Summary: Complete Standardization

### Backend Eliminates:
- ❌ Dead `_poll_loop` code
- ❌ Duplicate poll loops (PRTG)
- ❌ ThreadPoolExecutor (Milestone, Cisco ASA)
- ❌ Inconsistent method signatures
- ❌ Scattered beat schedules
- ❌ Duplicate normalizer code
- ❌ Inconsistent clear event detection
- ❌ Missing seed data

### Frontend Eliminates:
- ❌ Duplicate bulk import code (5+ copies → 1 component)
- ❌ Duplicate device list management
- ❌ Two configuration locations
- ❌ Missing connector forms
- ❌ Missing Siklu in mapping dropdown

### Establishes:
- ✅ Single polling mechanism (Celery)
- ✅ Consistent async architecture (aiohttp, asyncssh)
- ✅ Standardized backend method signatures
- ✅ Reusable frontend components
- ✅ Single configuration location (ConfigModal)
- ✅ Consistent UI patterns
- ✅ **Standardized normalizer base class**
- ✅ **Database-driven mappings for ALL connectors**
- ✅ **Consistent clear event detection**
- ✅ **Complete seed data for all connectors**

---

---

# PART 9: ADDON/PLUGIN ARCHITECTURE

## 9.1 Vision Overview

Transform connector-normalizer pairs into **self-contained addon modules** that can be:
- Uploaded as a single package (zip file)
- Installed/uninstalled through the frontend UI
- Dynamically loaded without system restart
- Developed independently and distributed separately

### Two Addon Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **NMS Connectors** | Connect to other Network Management Systems | PRTG, MCP (Ciena), SolarWinds, Zabbix |
| **Device Connectors** | Connect directly to device types | Ubiquiti, Cradlepoint, Axis, Siklu, Cisco ASA |

---

## 9.2 Addon Package Structure

Each addon is a **zip file** with a standardized structure:

```
addon-prtg-v1.0.0.zip
├── manifest.json           # Metadata, dependencies, version
├── backend/
│   ├── connector.py        # Connector class (extends BaseConnector)
│   ├── normalizer.py       # Normalizer class (extends BaseNormalizer)
│   ├── tasks.py            # Celery tasks for polling
│   └── requirements.txt    # Python dependencies (if any)
├── frontend/
│   ├── ConfigForm.jsx      # React config form component
│   ├── DeviceList.jsx      # Optional device management component
│   └── index.js            # Frontend entry point
├── migrations/
│   └── 001_initial.sql     # Database migrations for this addon
├── seed_data/
│   └── mappings.sql        # Default severity/category mappings
└── assets/
    └── icon.svg            # Addon icon for UI
```

### manifest.json Schema

```json
{
  "id": "prtg",
  "name": "PRTG Network Monitor",
  "version": "1.0.0",
  "category": "nms",
  "description": "Connect to PRTG Network Monitor for centralized alerting",
  "author": "OpsConductor",
  "min_core_version": "2.0.0",
  "connector_class": "PRTGConnector",
  "normalizer_class": "PRTGNormalizer",
  "config_schema": {
    "type": "object",
    "required": ["host", "api_user", "api_passhash"],
    "properties": {
      "host": { "type": "string", "title": "PRTG Server URL" },
      "api_user": { "type": "string", "title": "API Username" },
      "api_passhash": { "type": "string", "title": "API Passhash", "sensitive": true },
      "poll_interval": { "type": "integer", "default": 60, "title": "Poll Interval (seconds)" }
    }
  },
  "capabilities": ["polling", "webhooks", "device_sync"],
  "dependencies": {
    "python": ["aiohttp>=3.8.0"],
    "system": []
  },
  "celery_tasks": [
    {
      "name": "poll_prtg_alerts",
      "schedule": "*/60 * * * * *",
      "task_path": "backend.tasks.poll_alerts"
    }
  ]
}
```

---

## 9.3 Backend Addon Architecture

### 9.3.1 Core Addon Manager

Create `backend/core/addon_manager.py`:

```python
class AddonManager:
    """Manages addon lifecycle: install, enable, disable, uninstall."""
    
    ADDON_STORAGE_PATH = "/var/opsconductor/addons"
    ADDON_REGISTRY_TABLE = "installed_addons"
    
    def __init__(self, db_connection, celery_app):
        self.db = db_connection
        self.celery = celery_app
        self._loaded_addons: Dict[str, LoadedAddon] = {}
    
    async def install_addon(self, zip_file: UploadFile) -> AddonInstallResult:
        """
        Install addon from uploaded zip file.
        
        Steps:
        1. Validate zip structure and manifest
        2. Check version compatibility
        3. Extract to addon storage
        4. Run database migrations
        5. Install Python dependencies
        6. Register in installed_addons table
        7. Load addon into runtime
        """
        pass
    
    async def uninstall_addon(self, addon_id: str) -> bool:
        """
        Uninstall addon.
        
        Steps:
        1. Stop any running tasks
        2. Unregister Celery tasks
        3. Remove from installed_addons table
        4. Optionally run down migrations
        5. Remove addon files
        """
        pass
    
    async def enable_addon(self, addon_id: str) -> bool:
        """Enable a disabled addon."""
        pass
    
    async def disable_addon(self, addon_id: str) -> bool:
        """Disable addon without uninstalling."""
        pass
    
    async def load_addon(self, addon_id: str) -> LoadedAddon:
        """
        Dynamically load addon into runtime.
        
        Steps:
        1. Import connector and normalizer modules
        2. Instantiate classes
        3. Register with ConnectorRegistry
        4. Register Celery tasks
        """
        pass
    
    def get_installed_addons(self) -> List[AddonInfo]:
        """List all installed addons with status."""
        pass
    
    def get_addon_config_schema(self, addon_id: str) -> dict:
        """Get JSON Schema for addon configuration."""
        pass
```

### 9.3.2 Database Schema for Addon Registry

Create migration `030_addon_registry.sql`:

```sql
CREATE TABLE installed_addons (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(32) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('nms', 'device')),
    description TEXT,
    author VARCHAR(255),
    enabled BOOLEAN DEFAULT true,
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    manifest JSONB NOT NULL,
    config JSONB DEFAULT '{}',
    storage_path VARCHAR(512) NOT NULL
);

CREATE TABLE addon_migrations (
    id SERIAL PRIMARY KEY,
    addon_id VARCHAR(64) REFERENCES installed_addons(id) ON DELETE CASCADE,
    migration_name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(addon_id, migration_name)
);

CREATE INDEX idx_installed_addons_category ON installed_addons(category);
CREATE INDEX idx_installed_addons_enabled ON installed_addons(enabled);
```

### 9.3.3 Dynamic Module Loading

```python
import importlib.util
import sys

class AddonLoader:
    """Dynamically loads Python modules from addon packages."""
    
    @staticmethod
    def load_module(addon_id: str, module_path: str, module_name: str):
        """
        Load a Python module from file path.
        
        Example: load_module("prtg", "/var/opsconductor/addons/prtg/backend/connector.py", "connector")
        """
        spec = importlib.util.spec_from_file_location(
            f"addons.{addon_id}.{module_name}",
            module_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"addons.{addon_id}.{module_name}"] = module
        spec.loader.exec_module(module)
        return module
    
    @staticmethod
    def get_class(module, class_name: str):
        """Get a class from a loaded module."""
        return getattr(module, class_name)
```

### 9.3.4 Celery Task Registration

```python
class DynamicTaskRegistry:
    """Register and unregister Celery tasks dynamically."""
    
    def __init__(self, celery_app):
        self.celery = celery_app
        self._addon_tasks: Dict[str, List[str]] = {}  # addon_id -> task names
    
    def register_addon_tasks(self, addon_id: str, tasks_module, task_configs: List[dict]):
        """
        Register Celery tasks from addon.
        
        task_configs from manifest.json celery_tasks array.
        """
        registered = []
        for task_config in task_configs:
            task_name = f"addons.{addon_id}.{task_config['name']}"
            task_func = getattr(tasks_module, task_config['name'])
            
            # Register task with Celery
            self.celery.task(name=task_name)(task_func)
            
            # Add to beat schedule if specified
            if task_config.get('schedule'):
                self.celery.conf.beat_schedule[task_name] = {
                    'task': task_name,
                    'schedule': crontab_from_string(task_config['schedule']),
                }
            
            registered.append(task_name)
        
        self._addon_tasks[addon_id] = registered
    
    def unregister_addon_tasks(self, addon_id: str):
        """Remove addon tasks from Celery."""
        for task_name in self._addon_tasks.get(addon_id, []):
            # Remove from beat schedule
            self.celery.conf.beat_schedule.pop(task_name, None)
            # Note: Can't fully unregister from Celery, but tasks won't run
        
        self._addon_tasks.pop(addon_id, None)
```

---

## 9.4 Frontend Addon Architecture

### 9.4.1 Addon Management Page

Create `frontend/src/pages/system/AddonsPage.jsx`:

```jsx
/**
 * Addon Management Page
 * 
 * Features:
 * - List installed addons (NMS vs Device categories)
 * - Upload new addon (drag & drop zip file)
 * - Enable/disable addons
 * - Uninstall addons
 * - View addon details and configuration
 */

const AddonsPage = () => {
  const [addons, setAddons] = useState({ nms: [], device: [] });
  const [uploading, setUploading] = useState(false);
  
  // Addon cards with enable/disable toggle and uninstall button
  // Upload zone with drag & drop support
  // Category tabs: NMS Connectors | Device Connectors
};
```

### 9.4.2 Dynamic Frontend Component Loading

For frontend components, use **dynamic imports**:

```jsx
// Addon frontend components are stored in public/addons/{addon_id}/
// They are loaded dynamically when the addon is active

const loadAddonComponent = async (addonId, componentName) => {
  try {
    // Components are bundled as UMD modules
    const module = await import(`/addons/${addonId}/${componentName}.js`);
    return module.default;
  } catch (error) {
    console.error(`Failed to load addon component: ${addonId}/${componentName}`);
    return null;
  }
};

// Usage in ConfigModal
const AddonConfigForm = lazy(() => loadAddonComponent(connector.addon_id, 'ConfigForm'));
```

### 9.4.3 API Endpoints for Addon Management

```python
# backend/routers/addons.py

@router.get("/addons")
async def list_addons():
    """List all installed addons."""
    pass

@router.post("/addons/install")
async def install_addon(file: UploadFile):
    """Upload and install addon from zip file."""
    pass

@router.delete("/addons/{addon_id}")
async def uninstall_addon(addon_id: str):
    """Uninstall addon."""
    pass

@router.post("/addons/{addon_id}/enable")
async def enable_addon(addon_id: str):
    """Enable addon."""
    pass

@router.post("/addons/{addon_id}/disable")
async def disable_addon(addon_id: str):
    """Disable addon."""
    pass

@router.get("/addons/{addon_id}/config-schema")
async def get_config_schema(addon_id: str):
    """Get JSON Schema for addon configuration."""
    pass
```

---

## 9.5 Addon Development SDK

### 9.5.1 Base Classes (Required to Extend)

```python
# backend/connectors/base.py - Already exists, ensure it's the standard

class BaseConnector(ABC):
    """All addon connectors must extend this."""
    
    connector_type: str  # e.g., "prtg"
    display_name: str    # e.g., "PRTG Network Monitor"
    category: str        # "nms" or "device"
    
    @abstractmethod
    async def test_connection(self, config: dict) -> ConnectionTestResult:
        """Test connectivity with provided configuration."""
        pass
    
    @abstractmethod
    async def poll_alerts(self, config: dict) -> List[RawAlert]:
        """Poll for alerts/events."""
        pass
    
    # Optional methods
    async def sync_devices(self, config: dict) -> List[Device]:
        """Sync device inventory (for device connectors)."""
        return []
    
    async def get_device_info(self, config: dict, device_id: str) -> DeviceInfo:
        """Get detailed info for a specific device."""
        return None


class BaseNormalizer(ABC):
    """All addon normalizers must extend this."""
    
    connector_type: str
    default_category: Category
    
    # Inherited methods (from Part 8 standardization)
    def _load_mappings(self) -> None: ...
    def is_event_enabled(self, event_type: str) -> bool: ...
    def _get_severity(self, event_type: str) -> Severity: ...
    def _get_category(self, event_type: str) -> Category: ...
    def is_clear_event(self, event_type: str, raw_data: dict) -> bool: ...
    
    @abstractmethod
    def normalize(self, raw_data: dict) -> Optional[NormalizedAlert]:
        """Transform raw data to NormalizedAlert."""
        pass
```

### 9.5.2 Addon Development Template

Create a template repository/generator for new addons:

```
opsconductor-addon-template/
├── manifest.json.template
├── backend/
│   ├── connector.py.template
│   ├── normalizer.py.template
│   └── tasks.py.template
├── frontend/
│   ├── ConfigForm.jsx.template
│   └── package.json
├── migrations/
│   └── 001_initial.sql.template
├── seed_data/
│   └── mappings.sql.template
├── build.sh                    # Build script to create zip
└── README.md                   # Development guide
```

---

## 9.6 Migration Path: Convert Existing Connectors to Addons

### Phase A1: Create Addon Infrastructure

1. Create `backend/core/addon_manager.py`
2. Create `backend/routers/addons.py`
3. Create database migration for `installed_addons` table
4. Create `frontend/src/pages/system/AddonsPage.jsx`

### Phase A2: Create "Built-in" Addons Directory

Keep existing connectors as "built-in" addons that ship with the system:

```
backend/
├── connectors/           # Base classes and registry
│   ├── base.py
│   └── registry.py
├── addons/               # Built-in addons (ship with system)
│   ├── prtg/
│   │   ├── manifest.json
│   │   ├── connector.py
│   │   ├── normalizer.py
│   │   └── tasks.py
│   ├── mcp/
│   ├── axis/
│   ├── cradlepoint/
│   ├── siklu/
│   ├── ubiquiti/
│   ├── cisco_asa/
│   ├── eaton/
│   └── milestone/
└── user_addons/          # User-installed addons (uploaded via UI)
```

### Phase A3: Refactor Existing Connectors

Convert each existing connector to addon format:
1. Create `manifest.json` for each
2. Move frontend components to addon structure
3. Move migrations to addon structure
4. Test loading via AddonManager

### Phase A4: Frontend Integration

1. Create AddonsPage for management
2. Update ConfigModal to use dynamic component loading
3. Update ConnectorsPage to show addon status
4. Add navigation to Addons page in System menu

---

## 9.7 Addon Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADDON LIFECYCLE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌────────────┐  │
│  │ Upload  │───▶│ Validate │───▶│ Extract │───▶│ Run        │  │
│  │ ZIP     │    │ Manifest │    │ Files   │    │ Migrations │  │
│  └─────────┘    └──────────┘    └─────────┘    └────────────┘  │
│                                                      │          │
│                                                      ▼          │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌────────────┐  │
│  │ Active  │◀───│ Register │◀───│ Install │◀───│ Register   │  │
│  │ & Ready │    │ Celery   │    │ Python  │    │ in DB      │  │
│  └─────────┘    │ Tasks    │    │ Deps    │    └────────────┘  │
│       │         └──────────┘    └─────────┘                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   RUNTIME OPERATIONS                     │   │
│  │  • Poll alerts via Celery tasks                         │   │
│  │  • Normalize alerts via registered normalizer           │   │
│  │  • Serve config UI via dynamic frontend loading         │   │
│  │  • Enable/Disable toggle available                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌────────────┐  │
│  │ Disable │───▶│ Stop     │───▶│ Remove  │───▶│ Uninstall  │  │
│  │ Request │    │ Tasks    │    │ from DB │    │ Files      │  │
│  └─────────┘    └──────────┘    └─────────┘    └────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9.8 Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Malicious code in addon** | Sandbox execution, code signing, admin-only install |
| **Dependency vulnerabilities** | Scan requirements.txt, use allowlist |
| **File system access** | Restrict addon to its own directory |
| **Database access** | Addon migrations run in separate schema or with prefix |
| **Network access** | Connectors only access configured endpoints |

### Recommended: Code Signing

```json
// manifest.json
{
  "signature": "sha256:abc123...",
  "signed_by": "OpsConductor Official",
  "certificate": "-----BEGIN CERTIFICATE-----..."
}
```

---

## 9.9 Addon Architecture Files to Create

| File | Purpose | Effort |
|------|---------|--------|
| `backend/core/addon_manager.py` | Core addon lifecycle management | High |
| `backend/core/addon_loader.py` | Dynamic Python module loading | Medium |
| `backend/core/dynamic_tasks.py` | Dynamic Celery task registration | Medium |
| `backend/routers/addons.py` | REST API for addon management | Medium |
| `backend/migrations/030_addon_registry.sql` | Database schema | Low |
| `frontend/src/pages/system/AddonsPage.jsx` | Addon management UI | Medium |
| `frontend/src/components/addons/AddonCard.jsx` | Addon display component | Low |
| `frontend/src/components/addons/AddonUpload.jsx` | Upload component | Low |
| `frontend/src/hooks/useAddons.js` | React hook for addon API | Low |
| `docs/ADDON_DEVELOPMENT_GUIDE.md` | Developer documentation | Medium |

---

## 9.10 Implementation Order

1. **Create addon infrastructure** (AddonManager, database tables, API endpoints)
2. **Create manifest.json** for each existing connector
3. **Restructure existing connectors** into addon directory format
4. **Implement dynamic loading** (Python modules, Celery tasks)
5. **Build frontend AddonsPage** with upload capability
6. **Implement dynamic frontend component loading**
7. **Test full lifecycle** (install → enable → poll → disable → uninstall)
8. **Create addon development template** and documentation

---

## Summary: Complete Standardization with Addon Architecture

### Backend Eliminates:
- ❌ Dead `_poll_loop` code
- ❌ Duplicate poll loops
- ❌ Inconsistent method signatures
- ❌ Hardcoded connector registration
- ❌ Static Celery task definitions

### Frontend Eliminates:
- ❌ Hardcoded connector forms
- ❌ Static connector list
- ❌ Manual connector management

### Establishes:
- ✅ Single polling mechanism (Celery)
- ✅ Consistent async architecture
- ✅ Standardized backend interfaces (BaseConnector, BaseNormalizer)
- ✅ Database-driven mappings for ALL connectors
- ✅ **Dynamic addon loading and unloading**
- ✅ **User-uploadable addon packages (zip)**
- ✅ **Addon marketplace-ready architecture**
- ✅ **Clear separation: NMS vs Device connectors**

---

## Estimated Total Effort (Updated)

| Area | Tasks | Effort |
|------|-------|--------|
| **Backend Connectors** | Remove dead code, migrate to async | 4-6 hours |
| **Frontend Config** | Create reusable components, refactor forms | 3-4 hours |
| **Alert Mappings** | Standardize normalizers, add seed data | 3-4 hours |
| **Addon Infrastructure** | AddonManager, API, database | 6-8 hours |
| **Convert to Addons** | Restructure existing connectors | 4-6 hours |
| **Frontend Addon UI** | AddonsPage, dynamic loading | 3-4 hours |
| **Testing** | Verify all connectors + addon lifecycle | 3-4 hours |
| **Documentation** | Addon development guide | 2-3 hours |
| **Total** | | **28-42 hours**
