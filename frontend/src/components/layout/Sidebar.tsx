import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Rocket, 
  Building2, 
  Target, 
  BarChart3,
  Package
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

  return (
    <div className="w-64 bg-white border-r border-gray-200 h-screen sticky top-0">
      {/* Logo/Title */}
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-primary-500">
          10K Insight Agent
        </h1>
      </div>

      {/* Navigation */}
      <nav className="p-4">
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

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 text-center">
          <p>© 2025 10K Insight Agent</p>
          <p className="mt-1">Powered by LangGraph & GPT-4</p>
        </div>
      </div>
    </div>
  );
};
