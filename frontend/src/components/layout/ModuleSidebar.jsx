import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Server, 
  Search, 
  FolderOpen,
  Plus,
  FileText,
  CalendarClock,
  Hammer,
  LayoutDashboard,
  Network,
  Zap,
  Bell,
  Activity,
  Users,
  User,
  Settings,
  Key,
  ScrollText,
  Info,
  Database,
  Shield,
  Wifi,
  Terminal,
  Archive,
  ChevronDown,
  ChevronRight,
  KeyRound,
  Clock,
  History,
  ShieldCheck,
  AlertTriangle,
  FileKey,
  Circle,
  Battery,
  Download,
  Radio
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Define sidebar navigation for each module
const moduleNavigation = {
  alerts: {
    title: 'Alert Center',
    sections: [
      {
        title: 'Monitoring',
        items: [
          { id: 'dashboard', label: 'Alert Dashboard', icon: LayoutDashboard, path: '/alerts' },
        ]
      },
      {
        title: 'Filter By Status',
        items: [
          { id: 'active', label: 'Active Alerts', icon: AlertTriangle, path: '/alerts?status=active' },
          { id: 'acknowledged', label: 'Acknowledged', icon: Circle, path: '/alerts?status=acknowledged' },
          { id: 'resolved', label: 'Resolved', icon: ShieldCheck, path: '/alerts?status=resolved' },
        ]
      }
    ]
  },
  connectors: {
    title: 'Connectors',
    sections: [
      {
        title: 'Management',
        items: [
          { id: 'all-connectors', label: 'All Connectors', icon: Radio, path: '/connectors' },
        ]
      }
    ]
  },
  dependencies: {
    title: 'Dependencies',
    sections: [
      {
        title: 'Management',
        items: [
          { id: 'all-deps', label: 'All Dependencies', icon: Network, path: '/dependencies' },
        ]
      }
    ]
  },
  inventory: {
    title: 'Inventory',
    sections: [
      {
        title: 'Browse',
        items: [
          { id: 'devices', label: 'All Devices', icon: Server, path: '/inventory/devices' },
        ]
      }
    ]
  },
  system: {
    title: 'System',
    sections: [
      {
        title: 'Configuration',
        items: [
          { id: 'settings', label: 'Settings', icon: Settings, path: '/system/settings' },
        ]
      },
      {
        title: 'Maintenance',
        items: [
          { id: 'logs', label: 'System Logs', icon: ScrollText, path: '/system/logs' },
          { id: 'about', label: 'About', icon: Info, path: '/system/about' },
        ]
      }
    ]
  }
};

// Settings sub-navigation
const settingsNavigation = [
  { id: 'general', label: 'General', icon: Settings, path: '/system/settings/general' },
  { id: 'database', label: 'Database', icon: Database, path: '/system/settings/database' },
  { id: 'security', label: 'Security', icon: Shield, path: '/system/settings/security' },
  { id: 'logging', label: 'Logging', icon: ScrollText, path: '/system/settings/logging' },
  { id: 'netbox', label: 'NetBox', icon: Server, path: '/system/settings/netbox' },
  { id: 'prtg', label: 'PRTG', icon: Activity, path: '/system/settings/prtg' },
  { id: 'mcp', label: 'Ciena MCP', icon: Network, path: '/system/settings/mcp' },
  { id: 'backup', label: 'Backup', icon: Archive, path: '/system/settings/backup' },
];

export function ModuleSidebar({ module, children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedSections, setExpandedSections] = React.useState({});
  
  const nav = moduleNavigation[module];
  if (!nav) return null;

  const isSettingsPage = location.pathname.startsWith('/system/settings');

  const toggleSection = (title) => {
    setExpandedSections(prev => ({
      ...prev,
      [title]: !prev[title]
    }));
  };

  const isActive = (path) => {
    if (path === '/system/settings' && isSettingsPage) return true;
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Module Title */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
          {nav.title}
        </h2>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto py-2">
        {nav.sections.map((section) => (
          <div key={section.title} className="mb-4">
            <div className="px-4 py-1">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                {section.title}
              </span>
            </div>
            <div className="mt-1 space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);
                
                // Special handling for Settings - show sub-nav when active
                if (item.id === 'settings' && isSettingsPage) {
                  return (
                    <div key={item.id}>
                      <button
                        onClick={() => navigate(item.path)}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                          "bg-blue-50 text-blue-700 border-r-2 border-blue-600"
                        )}
                      >
                        <Icon className="w-4 h-4" />
                        <span className="font-medium">{item.label}</span>
                      </button>
                      {/* Settings sub-navigation */}
                      <div className="ml-4 mt-1 space-y-0.5 border-l border-gray-200">
                        {settingsNavigation.map((subItem) => {
                          const SubIcon = subItem.icon;
                          const subActive = location.pathname === subItem.path;
                          return (
                            <button
                              key={subItem.id}
                              onClick={() => navigate(subItem.path)}
                              className={cn(
                                "w-full flex items-center gap-2 pl-4 pr-4 py-1.5 text-xs transition-colors",
                                subActive
                                  ? "text-blue-700 bg-blue-50 font-medium"
                                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                              )}
                            >
                              <SubIcon className="w-3 h-3" />
                              <span>{subItem.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                }
                
                return (
                  <button
                    key={item.id}
                    onClick={() => navigate(item.path)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                      active
                        ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600 font-medium"
                        : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* Custom content slot (e.g., device groups for inventory) */}
        {children}
      </div>
    </aside>
  );
}

export default ModuleSidebar;
