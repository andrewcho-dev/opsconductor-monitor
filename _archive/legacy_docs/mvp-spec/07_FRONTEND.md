# 07 - Frontend Modules

**OpsConductor MVP - UI Components & Pages**

---

## 1. Frontend Architecture

### 1.1 Technology Stack

| Component | Technology |
|-----------|------------|
| Framework | React 18+ |
| Build Tool | Vite |
| Styling | TailwindCSS |
| Components | shadcn/ui |
| Icons | Lucide React |
| State | React Context + Hooks |
| Routing | React Router v6 |
| API Client | fetch + custom hooks |

### 1.2 Project Structure

```
frontend/src/
├── components/
│   ├── alerts/              # Alert-specific components
│   │   ├── AlertCard.jsx
│   │   ├── AlertTable.jsx
│   │   ├── AlertFilters.jsx
│   │   ├── AlertActions.jsx
│   │   ├── AlertDetail.jsx
│   │   ├── AlertHistory.jsx
│   │   └── AlertStats.jsx
│   ├── dependencies/        # Dependency components
│   │   ├── DependencyGraph.jsx
│   │   ├── DependencyEditor.jsx
│   │   └── DependencyList.jsx
│   ├── connectors/          # Connector components
│   │   ├── ConnectorCard.jsx
│   │   ├── ConnectorConfig.jsx
│   │   └── ConnectorStatus.jsx
│   ├── layout/              # Layout components (existing)
│   │   ├── PageLayout.jsx
│   │   ├── PageHeader.jsx
│   │   ├── ModuleSidebar.jsx
│   │   └── Navbar.jsx
│   └── ui/                  # shadcn/ui components
│
├── pages/
│   ├── alerts/              # Alert pages
│   │   ├── AlertDashboard.jsx
│   │   ├── AlertDetailPage.jsx
│   │   └── index.jsx
│   ├── dependencies/        # Dependency pages
│   │   ├── DependenciesPage.jsx
│   │   └── DependencyEditorPage.jsx
│   ├── connectors/          # Connector pages
│   │   ├── ConnectorsPage.jsx
│   │   └── ConnectorConfigPage.jsx
│   └── system/              # System pages (existing)
│
├── hooks/
│   ├── useAlerts.js         # Alert data hooks
│   ├── useDependencies.js   # Dependency hooks
│   ├── useConnectors.js     # Connector hooks
│   ├── useWebSocket.js      # Real-time updates
│   └── useApi.js            # Generic API hook (existing)
│
├── contexts/
│   ├── AuthContext.jsx      # (existing)
│   └── AlertContext.jsx     # Real-time alert state
│
└── lib/
    ├── utils.js             # (existing)
    └── constants.js         # Severity colors, etc.
```

---

## 2. Module Navigation

### 2.1 Sidebar Structure

```
ALERTS (new module)
├── Dashboard          /alerts
├── Active Alerts      /alerts/active
├── All Alerts         /alerts/all
└── Alert History      /alerts/history

DEPENDENCIES (new module)
├── Overview           /dependencies
├── Device Graph       /dependencies/graph
└── Edit Dependencies  /dependencies/edit

CONNECTORS (new module)
├── Status             /connectors
└── Configure          /connectors/config

INVENTORY (existing - keep)
├── All Devices        /inventory/devices
├── By Site            /inventory/by-site
└── By Type            /inventory/by-type

SYSTEM (existing - keep)
├── Settings           /system/settings
├── Users              /system/users
└── Logs               /system/logs
```

### 2.2 Module Registration

```jsx
// src/components/layout/ModuleSidebar.jsx

const MODULE_CONFIGS = {
  alerts: {
    title: "Alerts",
    icon: Bell,
    items: [
      { path: "/alerts", label: "Dashboard", icon: LayoutDashboard },
      { path: "/alerts/active", label: "Active Alerts", icon: AlertCircle },
      { path: "/alerts/all", label: "All Alerts", icon: List },
      { path: "/alerts/history", label: "History", icon: History },
    ],
  },
  dependencies: {
    title: "Dependencies",
    icon: Network,
    items: [
      { path: "/dependencies", label: "Overview", icon: Eye },
      { path: "/dependencies/graph", label: "Device Graph", icon: GitBranch },
      { path: "/dependencies/edit", label: "Edit", icon: Edit },
    ],
  },
  connectors: {
    title: "Connectors",
    icon: Plug,
    items: [
      { path: "/connectors", label: "Status", icon: Activity },
      { path: "/connectors/config", label: "Configure", icon: Settings },
    ],
  },
  // ... existing modules
};
```

---

## 3. Alert Dashboard (Main Page)

### 3.1 Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER: Alert Dashboard                              [Filters] [⚙]  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │CRITICAL │ │  MAJOR  │ │  MINOR  │ │ WARNING │ │  TOTAL  │        │
│  │   5     │ │   12    │ │   18    │ │   7     │ │   42    │        │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ FILTERS: [Severity ▼] [Category ▼] [Source ▼] [Search...]     │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ ○ SEV  TITLE                    DEVICE       TIME      ACTIONS│   │
│  ├───────────────────────────────────────────────────────────────┤   │
│  │ ● CRI  Interface Down Gi0/1     Core-SW-1    2m ago    [Ack]  │   │
│  │ ● MAJ  UPS On Battery           UPS-Main     5m ago    [Ack]  │   │
│  │ ● MAJ  Camera Offline           Cam-Lobby    10m ago   [Ack]  │   │
│  │ ○ MIN  High CPU Usage           Server-1     15m ago   [Ack]  │   │
│  │ ○ WRN  Signal Degraded          Radio-A      20m ago   [Ack]  │   │
│  │ ...                                                            │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [< Prev]  Page 1 of 3  [Next >]                                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component: AlertDashboard.jsx

```jsx
import { PageLayout, PageHeader } from '../../components/layout';
import { AlertStats } from '../../components/alerts/AlertStats';
import { AlertFilters } from '../../components/alerts/AlertFilters';
import { AlertTable } from '../../components/alerts/AlertTable';
import { useAlerts } from '../../hooks/useAlerts';

export function AlertDashboard() {
  const {
    alerts,
    stats,
    loading,
    error,
    filters,
    setFilters,
    pagination,
    refresh,
  } = useAlerts({ status: 'active' });

  return (
    <PageLayout module="alerts">
      <PageHeader
        title="Alert Dashboard"
        description="Real-time view of all active alerts"
        actions={
          <Button onClick={refresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        }
      />
      
      <div className="p-6 space-y-6">
        {/* Stats Cards */}
        <AlertStats stats={stats} />
        
        {/* Filters */}
        <AlertFilters filters={filters} onChange={setFilters} />
        
        {/* Alert Table */}
        <AlertTable
          alerts={alerts}
          loading={loading}
          pagination={pagination}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
          onSelect={handleSelect}
        />
      </div>
    </PageLayout>
  );
}
```

### 3.3 Real-time Updates

```jsx
// src/hooks/useAlerts.js

export function useAlerts(initialFilters = {}) {
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({});
  const { socket } = useWebSocket('/api/v1/ws/alerts');

  // Listen for real-time updates
  useEffect(() => {
    if (!socket) return;

    socket.onmessage = (event) => {
      const { type, data } = JSON.parse(event.data);
      
      switch (type) {
        case 'alert.created':
          setAlerts(prev => [data, ...prev]);
          break;
        case 'alert.updated':
          setAlerts(prev => prev.map(a => 
            a.id === data.id ? { ...a, ...data } : a
          ));
          break;
        case 'alert.resolved':
          setAlerts(prev => prev.filter(a => a.id !== data.id));
          break;
      }
    };
  }, [socket]);

  // ... rest of hook
}
```

---

## 4. Alert Detail Page

### 4.1 Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ ● CRITICAL    Interface Down - GigabitEthernet0/1              │   │
│  │                                                                 │   │
│  │ Device: Core-Switch-1 (10.1.1.1)                               │   │
│  │ Category: Network    Source: SNMP Trap    Occurred: 2m ago     │   │
│  │                                                                 │   │
│  │ [Acknowledge]  [Resolve]  [Add Note]                           │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────┐  ┌─────────────────────────────────┐   │
│  │ DETAILS                 │  │ HISTORY                          │   │
│  │                         │  │                                   │   │
│  │ Message:                │  │ • Created         2m ago          │   │
│  │ Interface went down...  │  │ • Acknowledged    1m ago (jsmith) │   │
│  │                         │  │   "Looking into it"               │   │
│  │ Alert Type: link_down   │  │                                   │   │
│  │ Priority: P1            │  │                                   │   │
│  │ Occurrences: 1          │  │                                   │   │
│  └─────────────────────────┘  └─────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ RELATED ALERTS (Correlated)                                    │   │
│  │                                                                 │   │
│  │ ○ Camera-Lobby offline (suppressed - depends on Core-Switch-1)│   │
│  │ ○ NVR-1 recording error (suppressed)                          │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ RAW DATA                                             [Expand]  │   │
│  │ { "trap_oid": "1.3.6.1.6.3.1.1.5.3", ... }                    │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Dependencies Page

### 5.1 Overview Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER: Device Dependencies                          [Add] [Import] │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                                 │
│  │ DEVICES │ │ DEPS    │ │ ORPHANS │                                 │
│  │   150   │ │   245   │ │   12    │                                 │
│  └─────────┘ └─────────┘ └─────────┘                                 │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ Search: [                    ]  Type: [All ▼]                  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ DEVICE          DEPENDS ON       TYPE      ACTIONS            │   │
│  ├───────────────────────────────────────────────────────────────┤   │
│  │ Camera-Lobby    Core-Switch-1    network   [Edit] [Delete]    │   │
│  │ Camera-Parking  Core-Switch-1    network   [Edit] [Delete]    │   │
│  │ NVR-1           Core-Switch-1    network   [Edit] [Delete]    │   │
│  │ NVR-1           UPS-Main         power     [Edit] [Delete]    │   │
│  │ ...                                                            │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Graph View

Visual representation of dependencies (future enhancement):

```
                    ┌─────────────┐
                    │  Internet   │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ Core-Router │
                    └──────┬──────┘
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴──────┐ ┌───┴────┐ ┌─────┴─────┐
       │Core-Switch-1│ │UPS-Main│ │Core-SW-2  │
       └──────┬──────┘ └───┬────┘ └─────┬─────┘
       ┌──────┴──────┐     │            │
       │             │     │      ┌─────┴─────┐
   ┌───┴───┐   ┌─────┴───┐ │      │  Server-1 │
   │Cam-1  │   │  NVR-1  │─┘      └───────────┘
   └───────┘   └─────────┘
```

---

## 6. Connectors Page

### 6.1 Status Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER: Connectors                                    [Add New]     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────┐  ┌─────────────────────┐              │   │
│  │ │ PRTG Production     │  │ MCP                  │              │   │
│  │ │ ● Connected         │  │ ● Connected          │              │   │
│  │ │ Last poll: 30s ago  │  │ Last poll: 45s ago   │              │   │
│  │ │ Alerts today: 42    │  │ Alerts today: 15     │              │   │
│  │ │ [Configure] [Test]  │  │ [Configure] [Test]   │              │   │
│  │ └─────────────────────┘  └─────────────────────┘              │   │
│  │                                                                 │   │
│  │ ┌─────────────────────┐  ┌─────────────────────┐              │   │
│  │ │ SNMP Traps          │  │ Eaton UPS           │              │   │
│  │ │ ● Listening :162    │  │ ● Connected (3)     │              │   │
│  │ │ Traps today: 156    │  │ Last poll: 20s ago  │              │   │
│  │ │ [Configure]         │  │ [Configure] [Test]  │              │   │
│  │ └─────────────────────┘  └─────────────────────┘              │   │
│  │                                                                 │   │
│  │ ┌─────────────────────┐  ┌─────────────────────┐              │   │
│  │ │ Axis Cameras        │  │ Milestone VMS       │              │   │
│  │ │ ○ Not configured    │  │ ○ Not configured    │              │   │
│  │ │                     │  │                      │              │   │
│  │ │ [Configure]         │  │ [Configure]         │              │   │
│  │ └─────────────────────┘  └─────────────────────┘              │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Configuration Form

```
┌──────────────────────────────────────────────────────────────────────┐
│  Configure: PRTG Connector                                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Name:        [PRTG Production                    ]                  │
│                                                                       │
│  Server URL:  [https://prtg.example.com           ]                  │
│                                                                       │
│  Authentication:                                                      │
│  ○ API Token  ● Username/Passhash                                    │
│                                                                       │
│  Username:    [admin                              ]                  │
│  Passhash:    [••••••••••••••                     ]                  │
│                                                                       │
│  □ Verify SSL Certificate                                            │
│  ☑ Enable connector                                                  │
│                                                                       │
│  Poll Interval: [60] seconds                                         │
│                                                                       │
│  [Test Connection]                    [Cancel]  [Save]               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Styling Constants

### 7.1 Severity Colors

```javascript
// src/lib/constants.js

export const SEVERITY_CONFIG = {
  critical: {
    color: 'red',
    bgClass: 'bg-red-500',
    textClass: 'text-red-500',
    badgeClass: 'bg-red-100 text-red-800',
    icon: AlertCircle,
  },
  major: {
    color: 'orange',
    bgClass: 'bg-orange-500',
    textClass: 'text-orange-500',
    badgeClass: 'bg-orange-100 text-orange-800',
    icon: AlertTriangle,
  },
  minor: {
    color: 'yellow',
    bgClass: 'bg-yellow-500',
    textClass: 'text-yellow-500',
    badgeClass: 'bg-yellow-100 text-yellow-800',
    icon: AlertTriangle,
  },
  warning: {
    color: 'blue',
    bgClass: 'bg-blue-500',
    textClass: 'text-blue-500',
    badgeClass: 'bg-blue-100 text-blue-800',
    icon: Info,
  },
  info: {
    color: 'gray',
    bgClass: 'bg-gray-500',
    textClass: 'text-gray-500',
    badgeClass: 'bg-gray-100 text-gray-800',
    icon: Info,
  },
  clear: {
    color: 'green',
    bgClass: 'bg-green-500',
    textClass: 'text-green-500',
    badgeClass: 'bg-green-100 text-green-800',
    icon: CheckCircle,
  },
};

export const CATEGORY_CONFIG = {
  network: { icon: Network, label: 'Network' },
  power: { icon: Zap, label: 'Power' },
  video: { icon: Video, label: 'Video' },
  wireless: { icon: Wifi, label: 'Wireless' },
  security: { icon: Shield, label: 'Security' },
  environment: { icon: Thermometer, label: 'Environment' },
  compute: { icon: Server, label: 'Compute' },
  storage: { icon: HardDrive, label: 'Storage' },
  application: { icon: Box, label: 'Application' },
  unknown: { icon: HelpCircle, label: 'Unknown' },
};

export const STATUS_CONFIG = {
  active: { color: 'red', label: 'Active' },
  acknowledged: { color: 'yellow', label: 'Acknowledged' },
  suppressed: { color: 'gray', label: 'Suppressed' },
  resolved: { color: 'green', label: 'Resolved' },
  expired: { color: 'gray', label: 'Expired' },
};
```

---

## 8. Pages to Keep/Remove

### 8.1 Keep (Existing)

| Page | Path | Notes |
|------|------|-------|
| Login | /login | No changes |
| Device List | /inventory/devices | Minor updates |
| Device Detail | /inventory/devices/:ip | Add alert widget |
| Settings | /system/settings | Add connector settings |
| Users | /system/users | No changes |
| Logs | /system/logs | No changes |

### 8.2 Remove/Hide

| Page | Reason |
|------|--------|
| Workflow Builder | Out of MVP scope |
| Job Scheduler | Out of MVP scope |
| Network Topology | Out of MVP scope |
| Power Trends | Out of MVP scope |
| IP Prefixes | Not needed |
| IP Ranges | Not needed |

### 8.3 New Pages

| Page | Path | Priority |
|------|------|----------|
| Alert Dashboard | /alerts | HIGH |
| Alert Detail | /alerts/:id | HIGH |
| Alert History | /alerts/history | MEDIUM |
| Dependencies | /dependencies | HIGH |
| Dependency Editor | /dependencies/edit | HIGH |
| Connectors | /connectors | HIGH |
| Connector Config | /connectors/:id | HIGH |

---

*Next: [08_IMPLEMENTATION_PLAN.md](./08_IMPLEMENTATION_PLAN.md)*
