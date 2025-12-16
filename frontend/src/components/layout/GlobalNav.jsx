import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Server, 
  Activity, 
  Settings,
  ChevronDown,
  GitBranch,
  KeyRound
} from 'lucide-react';
import { cn } from '../../lib/utils';

const modules = [
  { 
    id: 'inventory', 
    label: 'Inventory', 
    icon: Server, 
    path: '/inventory',
    description: 'Devices & Groups'
  },
  { 
    id: 'workflows', 
    label: 'Workflows', 
    icon: GitBranch, 
    path: '/workflows',
    description: 'Visual Automation Builder'
  },
  { 
    id: 'credentials', 
    label: 'Credentials', 
    icon: KeyRound, 
    path: '/credentials',
    description: 'Credential Vault'
  },
  { 
    id: 'monitor', 
    label: 'Monitor', 
    icon: Activity, 
    path: '/monitor',
    description: 'Dashboards & Alerts'
  },
  { 
    id: 'system', 
    label: 'System', 
    icon: Settings, 
    path: '/system',
    description: 'Settings & Infrastructure'
  },
];

export function GlobalNav() {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Determine active module from current path
  const activeModule = modules.find(m => location.pathname.startsWith(m.path))?.id || 'inventory';

  return (
    <nav className="bg-slate-900 text-white px-4 py-2 flex items-center justify-between shadow-lg">
      {/* Logo / Brand */}
      <div 
        className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => navigate('/inventory/devices')}
      >
        <img 
          src="/badge-light.svg" 
          alt="OpsConductor" 
          className="w-8 h-8"
        />
        <div className="hidden sm:block">
          <div className="font-bold text-lg leading-tight">OpsConductor</div>
          <div className="text-xs text-slate-400 leading-tight">Network Monitor</div>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex items-center gap-1">
        {modules.map((module) => {
          const Icon = module.icon;
          const isActive = activeModule === module.id;
          
          return (
            <button
              key={module.id}
              onClick={() => navigate(module.path)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                isActive 
                  ? "bg-blue-600 text-white shadow-md" 
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden md:inline">{module.label}</span>
            </button>
          );
        })}
      </div>

      {/* Right side - could add user menu, notifications, etc. */}
      <div className="flex items-center gap-2">
        <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span>System Online</span>
        </div>
      </div>
    </nav>
  );
}

export default GlobalNav;
