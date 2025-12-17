# OpsConductor Frontend

React application for OpsConductor, providing the user interface for device management, visual workflow building, monitoring, and system administration.

## Technology Stack

- **React 19** - UI framework
- **Vite 7** - Build tool and dev server
- **React Router 6** - Client-side routing
- **React Flow** - Visual workflow canvas
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **Chart.js / Recharts** - Data visualization

## Prerequisites

- **Node.js 18+**
- **Backend running** at `http://192.168.10.50:5000` (or adjust proxy in `vite.config.js`)

## Installation

```bash
npm install
```

## Development

Start the development server on port 3000:

```bash
npm run dev -- --host 0.0.0.0 --port 3000
```

The Vite dev server proxies API calls to the backend (configured in `vite.config.js`).

**Important:** The frontend must run on port 3000. Do not use other ports.

## Production Build

```bash
npm run build
```

Outputs to `../dist/` which Flask serves in production.

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Project Structure

```
src/
├── main.jsx              # React entry point
├── App.jsx               # Root component with routing
├── index.css             # Global styles (Tailwind)
│
├── api/                  # API Client
│   ├── client.js         # Base API client
│   ├── devices.js        # Device API
│   ├── groups.js         # Groups API
│   ├── workflows.js      # Workflows API
│   └── ...
│
├── components/           # Shared Components
│   ├── layout/           # PageLayout, GlobalNav, ModuleSidebar
│   ├── common/           # Button, Modal, Table, etc.
│   ├── auth/             # ProtectedRoute
│   └── ...
│
├── contexts/             # React Contexts
│   └── AuthContext.jsx   # Authentication state
│
├── features/             # Feature Modules
│   └── workflow-builder/ # Visual Workflow Builder
│       ├── components/   # Canvas, Toolbar, NodeEditor
│       ├── packages/     # 17 Node Packages
│       └── hooks/        # Workflow state management
│
├── hooks/                # Custom Hooks
│   ├── useApi.js         # Generic API hook
│   ├── useDevices.js     # Device data hook
│   ├── usePolling.js     # Polling hook
│   └── useNetBox.js      # NetBox integration
│
├── lib/                  # Utilities
│   └── utils.js          # Common utilities (cn, etc.)
│
└── pages/                # Page Components
    ├── auth/             # Login, Profile
    ├── inventory/        # Devices, Groups
    ├── workflows/        # Workflow List, Builder
    ├── monitor/          # Dashboard, Topology, Alerts
    ├── credentials/      # Credential Vault
    └── system/           # Settings, Users, Logs
```

## Application Modules

### Inventory (`/inventory`)
- **Devices** - Device list with search and filtering
- **Device Detail** - Interface status, power levels, LLDP
- **Groups** - Device group management

### Workflows (`/workflows`)
- **Workflow List** - Browse and manage workflows
- **Workflow Builder** - Visual drag-and-drop editor

### Monitor (`/monitor`)
- **Dashboard** - System overview
- **Topology** - Network topology visualization
- **Power Trends** - Optical power charts
- **Alerts** - Alert management
- **Active Jobs** - Running jobs
- **Job History** - Execution history

### Credentials (`/credentials`)
- **Credential Vault** - Encrypted credential storage

### System (`/system`)
- **Overview** - System health
- **Settings** - Application configuration
- **Users/Roles** - User and RBAC management
- **Notifications** - Notification channels
- **Logs** - System logs

## Page Layout Pattern

All pages use the standard `PageLayout` component:

```jsx
import { PageLayout, PageHeader } from '../../components/layout';

function MyPage() {
  return (
    <PageLayout module="inventory">
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

Valid module values: `inventory`, `workflows`, `monitor`, `credentials`, `system`

## Proxy Configuration

The Vite dev server proxies API requests to the backend. Edit `vite.config.js` to change the backend URL:

```javascript
proxy: {
  '/api': 'http://192.168.10.50:5000',
  '/data': 'http://192.168.10.50:5000',
  // ... more routes
}
```

## Documentation

See the main documentation in `docs/`:
- [FRONTEND.md](../docs/FRONTEND.md) - Detailed frontend architecture
- [WORKFLOW_BUILDER.md](../docs/WORKFLOW_BUILDER.md) - Workflow builder guide
- [API_REFERENCE.md](../docs/API_REFERENCE.md) - API documentation
