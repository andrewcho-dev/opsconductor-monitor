# OpsConductor Frontend Documentation

This document provides comprehensive documentation for the OpsConductor frontend, a React application built with Vite that provides the user interface for device management, workflow building, monitoring, and system administration.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Application Entry Point](#application-entry-point)
4. [Routing](#routing)
5. [Page Modules](#page-modules)
6. [Components](#components)
7. [API Client](#api-client)
8. [Hooks](#hooks)
9. [Features](#features)
10. [Styling](#styling)
11. [Build & Development](#build--development)

---

## Architecture Overview

The frontend is a single-page application (SPA) built with:

- **React 19** - UI framework with functional components and hooks
- **Vite 7** - Fast build tool and development server
- **React Router 6** - Client-side routing
- **TailwindCSS** - Utility-first CSS framework
- **React Flow** - Visual workflow canvas
- **Lucide React** - Icon library

```
┌─────────────────────────────────────────────────────────────┐
│                        App.jsx                               │
│                   (Router + AuthProvider)                    │
├─────────────────────────────────────────────────────────────┤
│                      Page Components                         │
│   Inventory | Workflows | Monitor | Credentials | System    │
├─────────────────────────────────────────────────────────────┤
│                    Layout Components                         │
│         GlobalNav | ModuleSidebar | PageLayout              │
├─────────────────────────────────────────────────────────────┤
│                    Feature Components                        │
│              Workflow Builder | Device Table                 │
├─────────────────────────────────────────────────────────────┤
│                      API Client                              │
│           Centralized fetch with error handling              │
├─────────────────────────────────────────────────────────────┤
│                    Custom Hooks                              │
│      useDevices | useApi | usePolling | useNetBox           │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
frontend/
├── index.html              # HTML entry point
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite configuration with proxy
├── tailwind.config.js      # Tailwind CSS configuration
├── postcss.config.js       # PostCSS configuration
├── eslint.config.js        # ESLint configuration
│
├── public/                 # Static assets
│   └── favicon.ico
│
└── src/
    ├── main.jsx            # React entry point
    ├── App.jsx             # Root component with routing
    ├── index.css           # Global styles
    │
    ├── api/                # API Client Modules
    │   ├── client.js       # Base API client
    │   ├── devices.js      # Device API
    │   ├── groups.js       # Groups API
    │   ├── jobs.js         # Jobs API
    │   ├── scans.js        # Scans API
    │   ├── scheduler.js    # Scheduler API
    │   ├── workflows.js    # Workflows API
    │   └── index.js        # API exports
    │
    ├── components/         # Shared Components
    │   ├── layout/         # Layout components
    │   │   ├── GlobalNav.jsx      # Top navigation bar
    │   │   ├── ModuleSidebar.jsx  # Module-specific sidebar
    │   │   ├── PageLayout.jsx     # Standard page wrapper
    │   │   └── PageHeader.jsx     # Page title/description
    │   ├── common/         # Common UI components
    │   │   ├── Button.jsx
    │   │   ├── Modal.jsx
    │   │   ├── Table.jsx
    │   │   └── ...
    │   ├── auth/           # Auth components
    │   │   └── ProtectedRoute.jsx
    │   ├── workflows/      # Workflow components
    │   ├── DeviceTable.jsx
    │   ├── GroupModal.jsx
    │   ├── ScanProgress.jsx
    │   ├── SettingsModal.jsx
    │   └── Sidebar.jsx
    │
    ├── contexts/           # React Contexts
    │   └── AuthContext.jsx # Authentication state
    │
    ├── features/           # Feature Modules
    │   └── workflow-builder/  # Visual Workflow Builder
    │       ├── components/    # Builder UI components
    │       ├── hooks/         # Builder-specific hooks
    │       ├── packages/      # Node package definitions
    │       ├── nodes/         # Custom node components
    │       ├── utils/         # Builder utilities
    │       └── index.jsx      # Feature export
    │
    ├── hooks/              # Custom Hooks
    │   ├── useApi.js       # Generic API hook
    │   ├── useDevices.js   # Device data hook
    │   ├── useNetBox.js    # NetBox integration hook
    │   ├── usePolling.js   # Polling hook
    │   └── index.js        # Hook exports
    │
    ├── lib/                # Utility Libraries
    │   └── utils.js        # Common utilities
    │
    └── pages/              # Page Components
        ├── auth/           # Authentication pages
        │   ├── LoginPage.jsx
        │   └── ProfilePage.jsx
        ├── inventory/      # Inventory module
        │   ├── DevicesPage.jsx
        │   ├── DeviceDetailPage.jsx
        │   ├── GroupsPage.jsx
        │   └── index.jsx
        ├── workflows/      # Workflows module
        │   ├── WorkflowsListPage.jsx
        │   ├── WorkflowBuilderPage.jsx
        │   └── index.jsx
        ├── monitor/        # Monitor module
        │   ├── DashboardPage.jsx
        │   ├── TopologyPage.jsx
        │   ├── PowerTrendsPage.jsx
        │   ├── AlertsPage.jsx
        │   ├── ActiveJobsPage.jsx
        │   ├── JobHistoryPage.jsx
        │   └── index.jsx
        ├── credentials/    # Credentials module
        │   ├── CredentialVaultPage.jsx
        │   └── index.jsx
        └── system/         # System module
            ├── SystemOverviewPage.jsx
            ├── SettingsPage.jsx
            ├── UsersPage.jsx
            ├── RolesPage.jsx
            ├── NotificationsPage.jsx
            ├── LogsPage.jsx
            ├── WorkersPage.jsx
            ├── AlertsPage.jsx
            ├── AboutPage.jsx
            ├── settings/   # Settings sub-pages
            │   ├── GeneralSettings.jsx
            │   ├── DatabaseSettings.jsx
            │   ├── SecuritySettings.jsx
            │   ├── LoggingSettings.jsx
            │   ├── NetBoxSettings.jsx
            │   └── BackupSettings.jsx
            └── index.jsx
```

---

## Application Entry Point

### main.jsx

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### App.jsx

The root component sets up routing and authentication:

```jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Auth routes */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <Navigate to="/monitor/dashboard" replace />
            </ProtectedRoute>
          } />
          
          {/* Module routes... */}
        </Routes>
      </AuthProvider>
    </Router>
  );
}
```

---

## Routing

### Route Structure

| Path | Component | Permission |
|------|-----------|------------|
| `/login` | `LoginPage` | Public |
| `/profile` | `ProfilePage` | Authenticated |
| `/` | Redirect to `/monitor/dashboard` | Authenticated |

#### Inventory Module

| Path | Component | Permission |
|------|-----------|------------|
| `/inventory` | Redirect to `/inventory/devices` | - |
| `/inventory/devices` | `DevicesPage` | `devices.device.view` |
| `/inventory/devices/:ip` | `DeviceDetailPage` | `devices.device.view` |
| `/inventory/groups` | `GroupsPage` | `devices.group.manage` |

#### Workflows Module

| Path | Component | Permission |
|------|-----------|------------|
| `/workflows` | `WorkflowsListPage` | `jobs.job.view` |
| `/workflows/new` | `WorkflowBuilderPage` | `jobs.job.create` |
| `/workflows/:id` | `WorkflowBuilderPage` | `jobs.job.view` |

#### Monitor Module

| Path | Component | Permission |
|------|-----------|------------|
| `/monitor` | Redirect to `/monitor/dashboard` | - |
| `/monitor/dashboard` | `DashboardPage` | Authenticated |
| `/monitor/topology` | `TopologyPage` | Authenticated |
| `/monitor/power` | `PowerTrendsPage` | Authenticated |
| `/monitor/alerts` | `AlertsPage` | Authenticated |
| `/monitor/active-jobs` | `ActiveJobsPage` | `jobs.job.view` |
| `/monitor/job-history` | `JobHistoryPage` | `jobs.job.view` |

#### Credentials Module

| Path | Component | Permission |
|------|-----------|------------|
| `/credentials` | `CredentialVaultPage` | `credentials.credential.view` |
| `/credentials/groups` | `CredentialVaultPage` | `credentials.group.manage` |
| `/credentials/expiring` | `CredentialVaultPage` | `credentials.credential.view` |
| `/credentials/audit` | `CredentialVaultPage` | `system.audit.view` |

#### System Module

| Path | Component | Permission |
|------|-----------|------------|
| `/system` | Redirect to `/system/overview` | - |
| `/system/overview` | `SystemOverviewPage` | `system.settings.view` |
| `/system/settings` | `SettingsPage` | `system.settings.view` |
| `/system/settings/general` | `GeneralSettings` | `system.settings.view` |
| `/system/settings/database` | `DatabaseSettings` | `system.settings.view` |
| `/system/settings/security` | `SecuritySettings` | `system.settings.view` |
| `/system/settings/logging` | `LoggingSettings` | `system.settings.view` |
| `/system/settings/netbox` | `NetBoxSettings` | `system.settings.view` |
| `/system/settings/backup` | `BackupSettings` | `system.settings.view` |
| `/system/users` | `UsersPage` | `system.users.view` |
| `/system/roles` | `RolesPage` | `system.roles.manage` |
| `/system/notifications` | `NotificationsPage` | `system.settings.view` |
| `/system/logs` | `LogsPage` | `system.audit.view` |
| `/system/workers` | `WorkersPage` | `system.settings.view` |
| `/system/about` | `AboutPage` | Authenticated |

### Legacy Redirects

Old routes are redirected to new locations:

```jsx
<Route path="/scheduler" element={<Navigate to="/monitor/active-jobs" replace />} />
<Route path="/jobs" element={<Navigate to="/workflows" replace />} />
<Route path="/topology" element={<Navigate to="/monitor/topology" replace />} />
<Route path="/settings" element={<Navigate to="/system/settings" replace />} />
```

---

## Page Modules

### Standard Page Pattern

All pages follow a consistent pattern using `PageLayout`:

```jsx
import { PageLayout, PageHeader } from '../../components/layout';

function ExamplePage() {
  return (
    <PageLayout module="inventory">  {/* or "workflows", "monitor", "credentials", "system" */}
      <PageHeader
        title="Page Title"
        description="Page description"
      />
      <div className="p-6">
        {/* Page content */}
      </div>
    </PageLayout>
  );
}
```

### Module Exports

Each module has an `index.jsx` that exports its pages:

```jsx
// pages/inventory/index.jsx
export { DevicesPage } from './DevicesPage';
export { DeviceDetailPage } from './DeviceDetailPage';
export { GroupsPage } from './GroupsPage';
```

---

## Components

### Layout Components

#### PageLayout

Standard page wrapper with sidebar navigation:

```jsx
<PageLayout module="system">
  {children}
</PageLayout>
```

Props:
- `module` - Module identifier for sidebar (`inventory`, `workflows`, `monitor`, `credentials`, `system`)
- `children` - Page content

#### PageHeader

Page title and description:

```jsx
<PageHeader
  title="Devices"
  description="Manage network devices"
  actions={<Button>Add Device</Button>}
/>
```

Props:
- `title` - Page title
- `description` - Optional description
- `actions` - Optional action buttons

#### GlobalNav

Top navigation bar with module links and user menu.

#### ModuleSidebar

Module-specific sidebar with navigation links.

### Common Components

Located in `src/components/common/`:

| Component | Description |
|-----------|-------------|
| `Button` | Styled button with variants |
| `Modal` | Modal dialog |
| `Table` | Data table with sorting/filtering |
| `Input` | Form input |
| `Select` | Dropdown select |
| `Tabs` | Tab navigation |
| `Badge` | Status badge |
| `Card` | Content card |
| `Spinner` | Loading spinner |

### Auth Components

#### ProtectedRoute

Wraps routes that require authentication:

```jsx
<Route path="/dashboard" element={
  <ProtectedRoute permission="dashboard.view">
    <DashboardPage />
  </ProtectedRoute>
} />
```

Props:
- `permission` - Optional permission required
- `children` - Protected content

---

## API Client

### Base Client (`api/client.js`)

Centralized API client with error handling:

```javascript
class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.json());
    }

    return response.json();
  }

  get(endpoint) { return this.request(endpoint); }
  post(endpoint, data) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(data) }); }
  put(endpoint, data) { return this.request(endpoint, { method: 'PUT', body: JSON.stringify(data) }); }
  delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); }
}

export const apiClient = new ApiClient();
```

### Domain APIs

#### devices.js

```javascript
export const devicesApi = {
  getAll: () => apiClient.get('/api/devices'),
  getById: (id) => apiClient.get(`/api/devices/${id}`),
  create: (data) => apiClient.post('/api/devices', data),
  update: (id, data) => apiClient.put(`/api/devices/${id}`, data),
  delete: (id) => apiClient.delete(`/api/devices/${id}`),
  getInterfaces: (id) => apiClient.get(`/api/devices/${id}/interfaces`),
};
```

#### workflows.js

```javascript
export const workflowsApi = {
  getAll: (params) => apiClient.get('/api/workflows', { params }),
  getById: (id) => apiClient.get(`/api/workflows/${id}`),
  create: (data) => apiClient.post('/api/workflows', data),
  update: (id, data) => apiClient.put(`/api/workflows/${id}`, data),
  delete: (id) => apiClient.delete(`/api/workflows/${id}`),
  execute: (id, data) => apiClient.post(`/api/workflows/${id}/execute`, data),
  getExecutions: (id) => apiClient.get(`/api/workflows/${id}/executions`),
};
```

---

## Hooks

### useApi

Generic hook for API calls with loading/error state:

```javascript
function useApi(apiFunction, dependencies = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await apiFunction();
        setData(result.data);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, dependencies);

  return { data, loading, error, refetch };
}

// Usage
const { data: devices, loading, error } = useApi(() => devicesApi.getAll());
```

### useDevices

Device-specific data hook:

```javascript
function useDevices() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDevices = async () => { /* ... */ };
  const createDevice = async (data) => { /* ... */ };
  const updateDevice = async (id, data) => { /* ... */ };
  const deleteDevice = async (id) => { /* ... */ };

  return { devices, loading, error, fetchDevices, createDevice, updateDevice, deleteDevice };
}
```

### usePolling

Polling hook for real-time updates:

```javascript
function usePolling(fetchFunction, interval = 5000) {
  const [data, setData] = useState(null);

  useEffect(() => {
    const poll = async () => {
      const result = await fetchFunction();
      setData(result);
    };

    poll();
    const timer = setInterval(poll, interval);
    return () => clearInterval(timer);
  }, [fetchFunction, interval]);

  return data;
}

// Usage
const status = usePolling(() => fetch('/api/status').then(r => r.json()), 3000);
```

### useNetBox

NetBox integration hook:

```javascript
function useNetBox() {
  const [sites, setSites] = useState([]);
  const [deviceRoles, setDeviceRoles] = useState([]);
  const [deviceTypes, setDeviceTypes] = useState([]);

  const fetchSites = async () => { /* ... */ };
  const fetchDeviceRoles = async () => { /* ... */ };
  const fetchDeviceTypes = async () => { /* ... */ };
  const syncDevice = async (deviceId) => { /* ... */ };

  return { sites, deviceRoles, deviceTypes, fetchSites, syncDevice };
}
```

---

## Features

### Workflow Builder

The workflow builder is a complex feature module located at `src/features/workflow-builder/`.

See [WORKFLOW_BUILDER.md](WORKFLOW_BUILDER.md) for detailed documentation.

Key components:
- `WorkflowBuilder.jsx` - Main builder component
- `WorkflowCanvas.jsx` - React Flow canvas
- `NodePalette.jsx` - Node selection sidebar
- `NodeEditor.jsx` - Node configuration modal
- `WorkflowToolbar.jsx` - Save/run/undo toolbar

---

## Styling

### TailwindCSS

The application uses TailwindCSS for styling:

```jsx
<button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
  Click me
</button>
```

### Configuration (`tailwind.config.js`)

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### Global Styles (`index.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom global styles */
```

### Utility Functions (`lib/utils.js`)

```javascript
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Usage
<div className={cn("base-class", condition && "conditional-class")} />
```

---

## Build & Development

### Development Server

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

The dev server runs on port 3000 with hot module replacement.

### Vite Configuration (`vite.config.js`)

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': 'http://192.168.10.50:5000',
      '/data': 'http://192.168.10.50:5000',
      '/progress': 'http://192.168.10.50:5000',
      // ... more proxy rules
    }
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  }
})
```

### Production Build

```bash
npm run build
```

Outputs to `../dist/` for Flask to serve.

### Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

### Dependencies

#### Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.2.0 | UI framework |
| `react-dom` | ^19.2.0 | React DOM renderer |
| `react-router-dom` | ^6.20.1 | Client-side routing |
| `reactflow` | ^11.11.4 | Workflow canvas |
| `lucide-react` | ^0.460.0 | Icons |
| `chart.js` | ^4.4.0 | Charts |
| `react-chartjs-2` | ^5.2.0 | React Chart.js wrapper |
| `recharts` | ^2.8.0 | Alternative charts |
| `clsx` | ^2.0.0 | Class name utility |
| `tailwind-merge` | ^2.1.0 | Tailwind class merging |
| `qrcode.react` | ^4.2.0 | QR code for 2FA |

#### Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `vite` | ^7.2.4 | Build tool |
| `@vitejs/plugin-react` | ^5.1.1 | React plugin for Vite |
| `tailwindcss` | ^3.3.6 | CSS framework |
| `autoprefixer` | ^10.4.16 | CSS autoprefixer |
| `postcss` | ^8.4.32 | CSS processing |
| `eslint` | ^9.39.1 | Linting |

---

## Authentication Context

### AuthContext (`contexts/AuthContext.jsx`)

Provides authentication state throughout the app:

```jsx
const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const login = async (username, password) => { /* ... */ };
  const logout = async () => { /* ... */ };
  const checkAuth = async () => { /* ... */ };
  const hasPermission = (permission) => { /* ... */ };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
```

### Usage

```jsx
function MyComponent() {
  const { user, hasPermission, logout } = useAuth();

  if (!hasPermission('admin.access')) {
    return <div>Access denied</div>;
  }

  return (
    <div>
      <p>Welcome, {user.username}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```
