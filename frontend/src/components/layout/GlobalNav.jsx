import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Server, 
  Activity, 
  Settings,
  ChevronDown,
  GitBranch,
  KeyRound,
  User,
  LogOut,
  Shield,
  Bell
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';

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
  const { user, isAuthenticated, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef(null);
  
  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // Determine active module from current path
  const activeModule = modules.find(m => location.pathname.startsWith(m.path))?.id || 'inventory';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

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

      {/* Right side - User menu */}
      <div className="flex items-center gap-3">
        <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span>System Online</span>
        </div>

        {isAuthenticated && user && (
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                {(user.display_name || user.username || '?')[0].toUpperCase()}
              </div>
              <span className="hidden md:block text-sm text-slate-300">{user.display_name || user.username}</span>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border py-1 z-50">
                <div className="px-4 py-3 border-b">
                  <p className="font-medium text-gray-900">{user.display_name || user.username}</p>
                  <p className="text-sm text-gray-500">{user.email}</p>
                  {user.roles && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {user.roles.map((role, idx) => (
                        <span key={idx} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                          {role}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => { navigate('/profile'); setShowUserMenu(false); }}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <User className="w-4 h-4" />
                  My Profile
                </button>
                <button
                  onClick={() => { navigate('/profile'); setShowUserMenu(false); }}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <Shield className="w-4 h-4" />
                  Security Settings
                </button>
                <div className="border-t my-1"></div>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}

export default GlobalNav;
