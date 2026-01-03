# OpsConductor Frontend Refactor Design

## Current State Analysis

The frontend already has a solid foundation:
- `useNetBox.js` hooks for fetching devices, sites, roles, tags from NetBox
- `DevicesPage.jsx` uses NetBox as primary device source
- Existing hooks in `useDevices.js` still reference local `/api/devices` endpoint

## Architecture Vision

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│  │  Device Inventory │    │  Performance     │    │  Health &     │ │
│  │  (from NetBox)    │    │  Metrics         │    │  Anomalies    │ │
│  └────────┬─────────┘    └────────┬─────────┘    └───────┬───────┘ │
│           │                       │                       │         │
│           ▼                       ▼                       ▼         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    API Layer (hooks)                          │  │
│  │  useNetBoxDevices()  useMetrics()  useHealthScores()          │  │
│  │  useNetBoxSites()    useOptical()  useAnomalies()             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND API                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  /api/netbox/*          → Proxy to NetBox API (inventory)           │
│  /api/metrics/*         → OpsConductor DB (time-series)             │
│  /api/health/*          → OpsConductor DB (health scores)           │
│  /api/anomalies/*       → OpsConductor DB (detected anomalies)      │
│  /api/baselines/*       → OpsConductor DB (baseline profiles)       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│        NetBox           │    │    OpsConductor DB      │
│   (Device Inventory)    │    │   (Performance Data)    │
└─────────────────────────┘    └─────────────────────────┘
```

## New/Modified Hooks

### 1. Enhanced NetBox Hooks (useNetBox.js)

Already have:
- `useNetBoxStatus()` - Connection status
- `useNetBoxDevices()` - Device list
- `useNetBoxDevice()` - Single device
- `useNetBoxLookups()` - Sites, roles, types
- `useNetBoxTags()` - Tags
- `useNetBoxIPRanges()` - IP ranges
- `useNetBoxPrefixes()` - IP prefixes

Add:
```javascript
// Fetch device interfaces from NetBox
export function useNetBoxInterfaces(deviceId) {
  // GET /api/netbox/devices/{id}/interfaces
}

// Fetch device connections/cables from NetBox
export function useNetBoxConnections(deviceId) {
  // GET /api/netbox/devices/{id}/connections
}
```

### 2. New Performance Metrics Hooks (useMetrics.js)

```javascript
// Optical power metrics
export function useOpticalMetrics(deviceIp, interfaceName, timeRange = '24h') {
  // GET /api/metrics/optical?device_ip={ip}&interface={name}&range={range}
  // Returns: { data: [...], baseline: {...} }
}

// Interface traffic metrics
export function useInterfaceMetrics(deviceIp, interfaceName, timeRange = '24h') {
  // GET /api/metrics/interface?device_ip={ip}&interface={name}&range={range}
}

// Path/latency metrics between two points
export function usePathMetrics(sourceIp, destIp, timeRange = '24h') {
  // GET /api/metrics/path?source={ip}&dest={ip}&range={range}
}

// Availability metrics for a device
export function useAvailabilityMetrics(deviceIp, timeRange = '7d') {
  // GET /api/metrics/availability?device_ip={ip}&range={range}
}

// Aggregated metrics (hourly/daily)
export function useAggregatedMetrics(deviceIp, metric, granularity = 'hourly', timeRange = '7d') {
  // GET /api/metrics/aggregated?device_ip={ip}&metric={name}&granularity={g}&range={range}
}
```

### 3. New Health & Anomaly Hooks (useHealth.js)

```javascript
// Health score for a device
export function useDeviceHealth(deviceIp) {
  // GET /api/health/device/{ip}
  // Returns: { overall: 95, availability: 100, performance: 90, ... }
}

// Health scores for a site
export function useSiteHealth(siteId) {
  // GET /api/health/site/{id}
}

// Network-wide health summary
export function useNetworkHealth() {
  // GET /api/health/network
}

// Active anomalies for a device
export function useDeviceAnomalies(deviceIp, options = {}) {
  // GET /api/anomalies?device_ip={ip}&severity={sev}&resolved={bool}
}

// All active anomalies (for dashboard)
export function useActiveAnomalies(options = {}) {
  // GET /api/anomalies?resolved=false&severity={sev}
}

// Baseline for a specific metric
export function useBaseline(deviceIp, interfaceName, metricName) {
  // GET /api/baselines?device_ip={ip}&interface={name}&metric={metric}
}
```

### 4. Deprecate/Remove (useDevices.js)

```javascript
// DEPRECATE: useDevices() - was fetching from local DB
// REPLACE WITH: useNetBoxDevices() from useNetBox.js

// KEEP: useGroups() - device groups are OpsConductor-specific
// But modify to use NetBox device IDs instead of local IDs

// DEPRECATE: useScanProgress() - old network scanner
// REPLACE WITH: usePollingStatus() for new polling system
```

## Page Refactoring

### 1. Device Detail Page (DeviceDetailPage.jsx)

**Current**: Shows basic device info
**New**: Comprehensive device view with performance data

```jsx
function DeviceDetailPage({ deviceIp }) {
  // Inventory from NetBox
  const { device } = useNetBoxDevice(deviceId);
  const { interfaces } = useNetBoxInterfaces(deviceId);
  
  // Performance from OpsConductor
  const { health } = useDeviceHealth(deviceIp);
  const { anomalies } = useDeviceAnomalies(deviceIp);
  const { metrics: availability } = useAvailabilityMetrics(deviceIp, '30d');
  
  return (
    <PageLayout module="inventory">
      {/* Device Info Card - from NetBox */}
      <DeviceInfoCard device={device} />
      
      {/* Health Score Card - from OpsConductor */}
      <HealthScoreCard health={health} />
      
      {/* Active Anomalies - from OpsConductor */}
      <AnomaliesCard anomalies={anomalies} />
      
      {/* Interfaces with Performance - merged */}
      <InterfacesTable 
        interfaces={interfaces}  // from NetBox
        metrics={...}            // from OpsConductor
      />
      
      {/* Availability Chart - from OpsConductor */}
      <AvailabilityChart data={availability} />
    </PageLayout>
  );
}
```

### 2. New Dashboard Page (DashboardPage.jsx)

**Current**: Basic monitoring dashboard
**New**: Network intelligence dashboard

```jsx
function DashboardPage() {
  // Health from OpsConductor
  const { health: networkHealth } = useNetworkHealth();
  const { anomalies } = useActiveAnomalies({ severity: 'critical' });
  
  // Inventory counts from NetBox
  const { devices } = useNetBoxDevices();
  const { lookups } = useNetBoxLookups();
  
  return (
    <PageLayout module="monitor">
      {/* Network Health Overview */}
      <NetworkHealthCard health={networkHealth} />
      
      {/* Site Health Map */}
      <SiteHealthMap sites={lookups.sites} />
      
      {/* Active Anomalies */}
      <AnomaliesPanel anomalies={anomalies} />
      
      {/* Device Status Summary */}
      <DeviceStatusSummary devices={devices} />
      
      {/* Performance Trends */}
      <PerformanceTrendsChart />
    </PageLayout>
  );
}
```

### 3. New Optical Monitoring Page (OpticalMonitorPage.jsx)

```jsx
function OpticalMonitorPage() {
  // Get optical-capable devices from NetBox (by role or tag)
  const { devices } = useNetBoxDevices({ role: 'switch' });
  
  // Get optical metrics for selected device
  const [selectedDevice, setSelectedDevice] = useState(null);
  const { metrics, baseline } = useOpticalMetrics(selectedDevice?.ip_address);
  
  return (
    <PageLayout module="monitor">
      {/* Device selector - from NetBox */}
      <DeviceSelector devices={devices} onSelect={setSelectedDevice} />
      
      {/* Optical power chart with baseline bands */}
      <OpticalPowerChart 
        metrics={metrics} 
        baseline={baseline}
      />
      
      {/* Interface optical status table */}
      <OpticalInterfacesTable deviceIp={selectedDevice?.ip_address} />
    </PageLayout>
  );
}
```

### 4. New Site Overview Page (SiteOverviewPage.jsx)

```jsx
function SiteOverviewPage({ siteId }) {
  // Site info from NetBox
  const { site } = useNetBoxSite(siteId);
  const { devices } = useNetBoxDevices({ site: siteId });
  
  // Health from OpsConductor
  const { health } = useSiteHealth(siteId);
  const { anomalies } = useActiveAnomalies({ site: siteId });
  
  return (
    <PageLayout module="inventory">
      {/* Site Info - from NetBox */}
      <SiteInfoCard site={site} />
      
      {/* Site Health - from OpsConductor */}
      <SiteHealthCard health={health} />
      
      {/* Devices at Site - from NetBox */}
      <DevicesTable devices={devices} />
      
      {/* Site Anomalies - from OpsConductor */}
      <AnomaliesTable anomalies={anomalies} />
    </PageLayout>
  );
}
```

## New Components

### 1. Health Score Components

```jsx
// Health score gauge (0-100)
<HealthGauge score={95} label="Overall Health" />

// Health trend sparkline
<HealthTrend data={healthHistory} trend={-2.5} />

// Health breakdown card
<HealthBreakdown 
  availability={100}
  performance={90}
  errors={95}
  capacity={85}
/>
```

### 2. Anomaly Components

```jsx
// Anomaly badge
<AnomalyBadge severity="critical" count={3} />

// Anomaly list item
<AnomalyItem 
  anomaly={anomaly}
  onAcknowledge={handleAck}
  onResolve={handleResolve}
/>

// Anomaly timeline
<AnomalyTimeline anomalies={anomalies} />
```

### 3. Metrics Chart Components

```jsx
// Time-series chart with baseline bands
<MetricsChart 
  data={metrics}
  baseline={baseline}
  showBands={true}
  yLabel="dBm"
/>

// Availability heatmap (like GitHub contribution graph)
<AvailabilityHeatmap data={dailyAvailability} />

// Latency distribution histogram
<LatencyHistogram data={latencyMetrics} />
```

### 4. Device Info Components (NetBox-sourced)

```jsx
// Device card with NetBox data
<DeviceCard 
  device={device}
  showHealth={true}  // Overlay health from OpsConductor
/>

// Interface list with optical status
<InterfaceList 
  interfaces={netboxInterfaces}
  opticalMetrics={opticalData}  // Merged from OpsConductor
/>
```

## API Endpoints (Backend)

### NetBox Proxy (existing, enhance)
- `GET /api/netbox/devices` - List devices
- `GET /api/netbox/devices/{id}` - Device detail
- `GET /api/netbox/devices/{id}/interfaces` - Device interfaces (NEW)
- `GET /api/netbox/sites` - List sites
- `GET /api/netbox/sites/{id}` - Site detail (NEW)

### Metrics API (new)
- `GET /api/metrics/optical` - Optical power readings
- `GET /api/metrics/interface` - Interface traffic/errors
- `GET /api/metrics/path` - Path latency/loss
- `GET /api/metrics/availability` - Device availability
- `GET /api/metrics/aggregated` - Pre-aggregated metrics

### Health API (new)
- `GET /api/health/device/{ip}` - Device health score
- `GET /api/health/site/{id}` - Site health score
- `GET /api/health/network` - Network-wide health

### Anomalies API (new)
- `GET /api/anomalies` - List anomalies (filterable)
- `POST /api/anomalies/{id}/acknowledge` - Acknowledge
- `POST /api/anomalies/{id}/resolve` - Mark resolved

### Baselines API (new)
- `GET /api/baselines` - Get baseline for metric
- `POST /api/baselines/calculate` - Trigger baseline recalculation

## Migration Steps

### Phase 1: Add New Hooks
1. Create `useMetrics.js` with performance metric hooks
2. Create `useHealth.js` with health/anomaly hooks
3. Add missing NetBox hooks (interfaces, connections)

### Phase 2: Update Existing Pages
1. Update `DeviceDetailPage` to show health + metrics
2. Update `DashboardPage` with network health overview
3. Update `PowerTrendsPage` to use new optical metrics API

### Phase 3: Create New Pages
1. Create `SiteOverviewPage`
2. Create `AnomaliesPage` (list all anomalies)
3. Create `NetworkHealthPage` (network-wide view)

### Phase 4: Remove Deprecated Code
1. Remove `useDevices()` hook (replace with `useNetBoxDevices`)
2. Remove local device API endpoints
3. Remove PRTG-related code (migration complete)

## File Structure

```
frontend/src/
├── hooks/
│   ├── useNetBox.js        # NetBox API hooks (inventory)
│   ├── useMetrics.js       # Performance metrics hooks (NEW)
│   ├── useHealth.js        # Health & anomaly hooks (NEW)
│   ├── usePolling.js       # Polling status hooks
│   └── index.js
├── components/
│   ├── health/             # Health score components (NEW)
│   │   ├── HealthGauge.jsx
│   │   ├── HealthTrend.jsx
│   │   └── HealthBreakdown.jsx
│   ├── anomalies/          # Anomaly components (NEW)
│   │   ├── AnomalyBadge.jsx
│   │   ├── AnomalyItem.jsx
│   │   └── AnomalyTimeline.jsx
│   ├── metrics/            # Metrics chart components (NEW)
│   │   ├── MetricsChart.jsx
│   │   ├── AvailabilityHeatmap.jsx
│   │   └── LatencyHistogram.jsx
│   └── devices/            # Device components
│       ├── DeviceCard.jsx
│       └── InterfaceList.jsx
├── pages/
│   ├── inventory/
│   │   ├── DevicesPage.jsx       # Uses NetBox
│   │   ├── DeviceDetailPage.jsx  # NetBox + OpsConductor
│   │   └── SiteOverviewPage.jsx  # NEW
│   ├── monitor/
│   │   ├── DashboardPage.jsx     # Enhanced with health
│   │   ├── OpticalMonitorPage.jsx
│   │   ├── AnomaliesPage.jsx     # NEW
│   │   └── NetworkHealthPage.jsx # NEW
│   └── ...
```

## Benefits

1. **Clear Separation of Concerns**
   - NetBox = What devices exist (inventory)
   - OpsConductor = How devices perform (metrics)

2. **No Data Duplication**
   - Device info fetched from NetBox
   - Performance data from OpsConductor
   - Merged in frontend as needed

3. **AI-Ready UI**
   - Health scores prominently displayed
   - Anomalies surfaced automatically
   - Baseline comparisons in charts

4. **Scalable Architecture**
   - Can add more metric types easily
   - Can add more health dimensions
   - Can integrate AI predictions later
