import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { MsalProvider } from '@azure/msal-react';
import { PublicClientApplication } from '@azure/msal-browser';
import { msalConfig } from './config/authConfig';
import { Sidebar } from './components/layout/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AnalysisQueue from './pages/AnalysisQueue';
import CompanyInsights from './pages/CompanyInsights';
import TopPitches from './pages/TopPitches';
import Metrics from './pages/Metrics';
import CatalogManager from './pages/CatalogManager';
import JobDetails from './pages/JobDetails';

// Initialize MSAL instance outside component to prevent re-initialization
const msalInstance = new PublicClientApplication(msalConfig);

const App: React.FC = () => {
  const [isInitialized, setIsInitialized] = React.useState(false);

  React.useEffect(() => {
    // Initialize MSAL and handle any pending redirects
    const initializeMsal = async () => {
      try {
        console.log('Initializing MSAL...');
        await msalInstance.initialize();
        
        console.log('Handling redirect promise...');
        const response = await msalInstance.handleRedirectPromise();
        
        if (response) {
          console.log('Authentication response received:', response.account?.username);
        } else {
          console.log('No pending redirect');
        }
        
        setIsInitialized(true);
      } catch (error) {
        console.error('MSAL initialization error:', error);
        setIsInitialized(true); // Continue anyway
      }
    };

    initializeMsal();
  }, []);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <MsalProvider instance={msalInstance}>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true
        }}
      >
        <Routes>
          {/* Public Route - Login */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected Routes */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <div className="flex h-screen overflow-hidden bg-gray-50">
                  {/* Sidebar */}
                  <Sidebar />
                  
                  {/* Main Content */}
                  <main className="flex-1 overflow-y-auto">
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/analysis-queue" element={<AnalysisQueue />} />
                      <Route path="/job/:jobId" element={<JobDetails />} />
                      <Route path="/company-insights" element={<CompanyInsights />} />
                      <Route path="/top-pitches" element={<TopPitches />} />
                      <Route path="/metrics" element={<Metrics />} />
                      <Route path="/catalog-manager" element={<CatalogManager />} />
                    </Routes>
                  </main>
                </div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </MsalProvider>
  );
};

export default App;
