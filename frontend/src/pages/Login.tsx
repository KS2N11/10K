import React from 'react';
import { useMsal, useIsAuthenticated } from '@azure/msal-react';
import { useNavigate } from 'react-router-dom';
import { loginRequest } from '../config/authConfig';
import { Building2, Lock, Shield, TrendingUp } from 'lucide-react';
import { InteractionStatus } from '@azure/msal-browser';

const Login: React.FC = () => {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const navigate = useNavigate();
  const [isLoggingIn, setIsLoggingIn] = React.useState(false);

  // Check if authentication is enabled
  const useAuth = import.meta.env.VITE_USE_AUTH === 'true';

  // Redirect to home if already authenticated or auth is disabled
  React.useEffect(() => {
    if (isAuthenticated || !useAuth) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, useAuth, navigate]);

  // Clear any stuck interaction state on mount
  React.useEffect(() => {
    const clearStuckState = () => {
      try {
        // Clear MSAL interaction status from storage
        const storage = sessionStorage;
        const keys = Object.keys(storage);
        keys.forEach(key => {
          if (key.includes('interaction.status')) {
            console.log('Removing stuck key:', key);
            storage.removeItem(key);
          }
        });
      } catch (error) {
        console.error('Error clearing storage:', error);
      }
    };

    // Only clear if we're stuck in progress state on the login page
    if (inProgress !== InteractionStatus.None && !isAuthenticated) {
      console.warn('Detected stuck interaction state on login page, clearing...');
      clearStuckState();
    }
  }, []); // Run only once on mount

  const handleLogin = async () => {
    // Prevent multiple simultaneous login attempts
    if (isLoggingIn) {
      console.log('Login already in progress, ignoring click');
      return;
    }

    // Check if MSAL is stuck in an interaction state
    if (inProgress !== InteractionStatus.None) {
      console.error('Cannot login: another interaction is in progress:', inProgress);
      alert('Authentication is in progress. Please wait or click "Reset" below if stuck.');
      return;
    }

    setIsLoggingIn(true);
    try {
      if (useAuth) {
        console.log('Starting login redirect...');
        // Use redirect instead of popup to avoid COOP issues
        await instance.loginRedirect(loginRequest);
      } else {
        // Bypass authentication - directly navigate to home
        navigate('/', { replace: true });
      }
    } catch (error) {
      console.error('Login failed:', error);
      alert('Login failed: ' + (error as Error).message);
      setIsLoggingIn(false);
    }
  };

  const handleReset = () => {
    // Clear all MSAL cache and reload
    try {
      sessionStorage.clear();
      localStorage.clear();
      window.location.reload();
    } catch (error) {
      console.error('Reset failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        {/* Left side - Branding and Features */}
        <div className="text-center lg:text-left space-y-6">
          <div className="flex items-center justify-center lg:justify-start gap-3 mb-8">
            <Building2 size={48} className="text-primary-600" />
            <h1 className="text-4xl font-bold text-gray-900">10K Insight</h1>
          </div>
          
          <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 leading-tight">
            AI-Powered SEC Filing Analysis
          </h2>
          
          <p className="text-xl text-gray-600">
            Automatically extract pain points and generate personalized sales pitches from company 10-K filings
          </p>

          <div className="space-y-4 mt-8">
            <div className="flex items-start gap-4">
              <div className="bg-primary-100 p-3 rounded-lg">
                <TrendingUp className="text-primary-600" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Smart Analysis</h3>
                <p className="text-gray-600 text-sm">Extract key pain points from SEC 10-K filings using AI</p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="bg-success-100 p-3 rounded-lg">
                <Building2 className="text-success-600" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Company Insights</h3>
                <p className="text-gray-600 text-sm">Browse and analyze thousands of public companies</p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="bg-blue-100 p-3 rounded-lg">
                <Shield className="text-blue-600" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Secure Access</h3>
                <p className="text-gray-600 text-sm">Protected by Microsoft Azure Active Directory</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login Card */}
        <div className="w-full max-w-md mx-auto">
          <div className="bg-white rounded-2xl shadow-2xl p-8 lg:p-10 border border-gray-100">
            <div className="text-center mb-8">
              <div className="bg-primary-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="text-primary-600" size={32} />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome Back</h2>
              <p className="text-gray-600">Sign in with your Microsoft account to continue</p>
            </div>

            <button
              onClick={handleLogin}
              disabled={isLoggingIn}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
            >
              {isLoggingIn ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Signing in...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
                    <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
                    <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
                    <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
                  </svg>
                  Sign in with Microsoft
                </>
              )}
            </button>

            {inProgress !== InteractionStatus.None && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800 text-center mb-2">
                  Authentication in progress...
                </p>
                <button
                  onClick={handleReset}
                  className="w-full text-sm text-yellow-700 hover:text-yellow-900 underline"
                >
                  Stuck? Click here to reset
                </button>
              </div>
            )}

            <div className="mt-6 text-center text-sm text-gray-500">
              <p>Secured by Azure Active Directory</p>
            </div>

            <div className="mt-8 pt-6 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                By signing in, you agree to our Terms of Service and Privacy Policy.
                This application uses Microsoft authentication for secure access.
              </p>
            </div>
          </div>

          {/* Additional info */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Need help? Contact your administrator
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
