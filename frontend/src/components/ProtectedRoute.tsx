import React from 'react';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Protected Route Component
 * Redirects to login if user is not authenticated (when auth is enabled)
 * Bypasses authentication check if VITE_USE_AUTH is false
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const isAuthenticated = useIsAuthenticated();
  const { inProgress } = useMsal();
  const useAuth = import.meta.env.VITE_USE_AUTH === 'true';

  // If authentication is disabled, allow access
  if (!useAuth) {
    return <>{children}</>;
  }

  // Show loading while authentication is in progress
  if (inProgress === "login" || inProgress === "handleRedirect") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Authenticating...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Render protected content
  return <>{children}</>;
};

export default ProtectedRoute;
