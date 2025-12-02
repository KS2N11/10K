import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useMsal, useIsAuthenticated } from '@azure/msal-react';
import { 
  LayoutDashboard, 
  Rocket, 
  Building2, 
  Target, 
  BarChart3,
  Package,
  LogOut,
  User
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/analysis-queue', label: 'Analysis Queue', icon: Rocket },
  { path: '/company-insights', label: 'Company Insights', icon: Building2 },
  { path: '/top-pitches', label: 'Top Pitches', icon: Target },
  { path: '/catalog-manager', label: 'Product Catalog', icon: Package },
  { path: '/metrics', label: 'Metrics', icon: BarChart3 },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const useAuth = import.meta.env.VITE_USE_AUTH === 'true';

  const handleLogout = () => {
    instance.logoutRedirect({
      postLogoutRedirectUri: "/login"
    });
  };

  const userName = accounts[0]?.name || accounts[0]?.username || 'Developer';

  return (
    <div className="w-64 bg-white border-r border-gray-200 h-screen sticky top-0 flex flex-col">
      {/* Logo/Title */}
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-primary-500">
          10K Insight Agent
        </h1>
      </div>

      {/* User Info */}
      {(isAuthenticated || !useAuth) && (
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="bg-primary-100 p-2 rounded-full">
              <User size={20} className="text-primary-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{userName}</p>
              <p className="text-xs text-gray-500">{useAuth ? 'Authenticated' : 'Dev Mode'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="p-4 flex-1 overflow-y-auto">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200
                    ${isActive 
                      ? 'bg-primary-500 text-white' 
                      : 'text-gray-700 hover:bg-gray-100'
                    }
                  `}
                >
                  <Icon size={20} />
                  <span className="font-medium">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Logout Button */}
      {isAuthenticated && useAuth && (
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors duration-200 font-medium"
          >
            <LogOut size={20} />
            Sign Out
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 text-center">
          <p>© 2025 10K Insight Agent</p>
          <p className="mt-1">Powered by LangGraph & GPT-4</p>
        </div>
      </div>
    </div>
  );
};
